"""Check composed authentication and access error boundaries."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from aiolimiter import AsyncLimiter

from api.config.cookies import ACCESS_TOKEN_COOKIE_NAME
from authorisation.jwt import create_token
from authorisation.jwt.config import get_jwt_secret
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.lifecycle import get_limiter
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


async def test_access_returns_identity_and_limits_ip_once(
	client: httpx.AsyncClient,
) -> None:
	"""Reuse the IP gate without charging a second allowance."""
	client.cookies.set(
		ACCESS_TOKEN_COOKIE_NAME, create_token('visitor')
	)
	with (
		patch(
			'api.dependencies.auth._checks.get_limiter',
			new_callable=AsyncMock,
			wraps=get_limiter,
		) as retrieve,
		patch(
			'api.dependencies.auth._checks.'
			'enforce_existing_block',
			new_callable=AsyncMock,
		) as check,
	):
		response = await client.get('/protected')
	assert response.status_code == 200
	assert response.json() == {
		'user_id': 'visitor',
		'ip': '127.0.0.1',
	}
	assert retrieve.await_count == 2
	assert [call.args for call in retrieve.await_args_list] == [
		(
			ResourceScope.APPLICATION,
			ResourceAccessor.IP,
			'127.0.0.1',
		),
		(
			ResourceScope.APPLICATION,
			ResourceAccessor.USER,
			'visitor',
		),
	]
	assert [call.args for call in check.await_args_list] == [
		(BlockedEntity.IP, '127.0.0.1'),
		(BlockedEntity.USER, 'visitor'),
	]


@pytest.mark.parametrize(
	'credential', ['missing', 'bad', 'expired']
)
async def test_invalid_credentials_still_pass_ip_gate(
	client: httpx.AsyncClient, credential: str
) -> None:
	"""Apply the IP allowance before rejecting credentials."""
	if credential == 'bad':
		client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, 'bad-token')
	elif credential == 'expired':
		now = get_utc_datetime_now()
		token = jwt.encode(
			{
				'sub': 'visitor',
				'iat': now - timedelta(days=2),
				'exp': now - timedelta(days=1),
			},
			get_jwt_secret(),
			algorithm='HS256',
		)
		client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)
	with patch(
		'api.dependencies.auth._checks.get_limiter',
		new_callable=AsyncMock,
		wraps=get_limiter,
	) as retrieve:
		response = await client.get('/protected')
	assert response.status_code == 401
	retrieve.assert_awaited_once_with(
		ResourceScope.APPLICATION,
		ResourceAccessor.IP,
		'127.0.0.1',
	)


@pytest.mark.parametrize('entity', list(BlockedEntity))
async def test_stored_blocks_deny_access(
	client: httpx.AsyncClient, entity: BlockedEntity
) -> None:
	"""Reject both entity kinds without revealing reasons."""
	client.cookies.set(
		ACCESS_TOKEN_COOKIE_NAME, create_token('visitor')
	)
	now = get_utc_datetime_now()
	record = BlockedRecord(
		entity=entity,
		entity_id='visitor',
		blocked_at=now,
		blocked_until=now + timedelta(days=1),
		reason='private blocking detail',
	)

	async def check(kind: BlockedEntity, identity: str) -> None:
		if kind == entity:
			raise EntityBlockedException(record)

	with patch(
		'api.dependencies.auth._checks.enforce_existing_block',
		new_callable=AsyncMock,
		side_effect=check,
	):
		response = await client.get('/protected')
	assert response.status_code == 403
	assert response.json() == {'detail': 'Access is blocked.'}


@pytest.mark.parametrize('failure', ['jwt', 'database', 'store'])
async def test_application_failures_are_server_errors(
	client: httpx.AsyncClient,
	monkeypatch: pytest.MonkeyPatch,
	failure: str,
) -> None:
	"""Do not report configuration or storage faults as 401."""
	client.cookies.set(
		ACCESS_TOKEN_COOKIE_NAME, create_token('visitor')
	)
	if failure == 'jwt':
		monkeypatch.delenv('JWT_SECRET')
	elif failure == 'database':
		monkeypatch.setattr(
			'api.dependencies.auth._checks.'
			'enforce_existing_block',
			AsyncMock(
				side_effect=RuntimeError('private failure')
			),
		)
	else:
		monkeypatch.setattr(
			'api.dependencies.auth._checks.get_limiter',
			AsyncMock(
				side_effect=RuntimeError('private failure')
			),
		)
	response = await client.get('/protected')
	assert response.status_code == 500
	assert 'private failure' not in response.text
	assert 'JWT_SECRET' not in response.text


@pytest.mark.parametrize('accessor', list(ResourceAccessor))
async def test_exhausted_allowances_return_429(
	client: httpx.AsyncClient, accessor: ResourceAccessor
) -> None:
	"""Reject exhausted IP or user capacity promptly."""
	client.cookies.set(
		ACCESS_TOKEN_COOKIE_NAME, create_token('visitor')
	)
	limits = {
		kind: AsyncLimiter(1, 3600) for kind in ResourceAccessor
	}
	await limits[accessor].acquire()

	async def retrieve(scope, kind, identity) -> AsyncLimiter:
		return limits[kind]

	with patch(
		'api.dependencies.auth._checks.get_limiter',
		new_callable=AsyncMock,
		side_effect=retrieve,
	):
		response = await client.get('/protected')
	assert response.status_code == 429
