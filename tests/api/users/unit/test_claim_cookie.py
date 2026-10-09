"""Check cookie claiming without external services."""

from collections.abc import AsyncIterator
from datetime import timedelta
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI

from api.dependencies.auth.ip import require_ip_access
from api.middleware.origin import OriginMiddleware
from api.routes import users
from authorisation.jwt.create import create_token
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from security import lifecycle
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


@pytest.fixture
def user_lookup(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncMock:
	"""Replace the user existence check with a typed mock."""
	lookup = AsyncMock(return_value=True)
	monkeypatch.setattr(users, 'does_user_exist', lookup)
	return lookup


@pytest_asyncio.fixture
async def client(
	monkeypatch: pytest.MonkeyPatch,
	user_lookup: AsyncMock,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Mount the real route and IP gate with isolated clients."""
	monkeypatch.setenv('JWT_SECRET', 'claim-cookie-test-' * 3)
	monkeypatch.setenv('CORS_ORIGINS', 'https://portfolio.test')
	monkeypatch.setenv('COOKIE_DOMAIN', 'api.test')
	monkeypatch.setattr(lifecycle, '_security_client', None)
	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		AsyncMock(),
	)
	await lifecycle.start_security_client()
	app = FastAPI()
	app.include_router(
		users.router,
		prefix='/users',
		dependencies=[Depends(require_ip_access)],
	)
	app.add_middleware(
		OriginMiddleware,
		allowed_origins=['https://portfolio.test'],
		protected_prefixes=('/users', '/agent'),
	)
	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(app=app),
			base_url='https://api.test',
			headers={'Origin': 'https://portfolio.test'},
		) as instance:
			yield instance
	finally:
		await lifecycle.stop_security_client()


async def test_claim_sets_existing_token_with_bounded_expiry(
	client: httpx.AsyncClient,
	user_lookup: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Set a secure cookie bounded by the original expiry."""
	monkeypatch.setattr(
		'authorisation.jwt.create.get_utc_datetime_now',
		lambda: get_utc_datetime_now() - timedelta(days=1),
	)
	token = create_token('visitor')
	response = await client.post(
		'/users/claim-cookie',
		json={'claim_token': token},
		headers={'X-Request-ID': 'claim-request'},
	)
	assert response.status_code == 200
	assert response.json()['data'] is None
	assert response.json()['meta']['success'] is True
	assert (
		response.json()['meta']['request_id'] == 'claim-request'
	)
	cookie = SimpleCookie(response.headers['set-cookie'])['JWT']
	assert cookie.value == token
	assert cookie['httponly'] and cookie['secure']
	assert cookie['samesite'] == 'lax'
	assert cookie['path'] == '/'
	assert cookie['domain'] == 'api.test'
	payload = jwt.decode(
		token, options={'verify_signature': False}
	)
	assert (
		parsedate_to_datetime(cookie['expires']).timestamp()
		== payload['exp']
	)
	assert (
		0
		< int(cookie['max-age'])
		<= (payload['exp'] - get_utc_datetime_now().timestamp())
	)
	user_lookup.assert_awaited_once_with('visitor')


@pytest.mark.parametrize(
	'body', [{}, {'claim_token': ''}, {'claim_token': 3}]
)
async def test_claim_rejects_invalid_body(
	client: httpx.AsyncClient,
	body: dict,
	user_lookup: AsyncMock,
) -> None:
	"""Require a non-empty token string before user lookups."""
	response = await client.post(
		'/users/claim-cookie', json=body
	)
	assert response.status_code == 422
	assert 'set-cookie' not in response.headers
	user_lookup.assert_not_awaited()


@pytest.mark.parametrize('expired', [False, True])
async def test_claim_rejects_invalid_or_expired_token(
	client: httpx.AsyncClient,
	expired: bool,
	monkeypatch: pytest.MonkeyPatch,
	user_lookup: AsyncMock,
) -> None:
	"""Never set cookies or query users for bad credentials."""
	token = 'invalid'
	if expired:
		monkeypatch.setattr(
			'authorisation.jwt.create.get_utc_datetime_now',
			lambda: get_utc_datetime_now() - timedelta(days=7),
		)
		token = create_token('visitor')
	response = await client.post(
		'/users/claim-cookie', json={'claim_token': token}
	)
	assert response.status_code == 401
	assert 'set-cookie' not in response.headers
	user_lookup.assert_not_awaited()


async def test_claim_rejects_missing_user(
	client: httpx.AsyncClient,
	user_lookup: AsyncMock,
) -> None:
	"""A valid signature cannot restore a deleted user."""
	user_lookup.return_value = False
	response = await client.post(
		'/users/claim-cookie',
		json={'claim_token': create_token('visitor')},
	)
	assert response.status_code == 404
	assert 'set-cookie' not in response.headers


@pytest.mark.parametrize('entity', list(BlockedEntity))
async def test_claim_rejects_blocked_identity(
	client: httpx.AsyncClient,
	entity: BlockedEntity,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Check both the client IP and verified user for blocks."""

	async def reject_blocked(target, identifier):
		if target == entity:
			raise EntityBlockedException(
				BlockedRecord(
					entity=entity,
					entity_id=identifier,
					blocked_at=get_utc_datetime_now(),
					blocked_until=(
						get_utc_datetime_now()
						+ timedelta(days=1)
					),
					reason='Private blocking reason',
				)
			)

	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		reject_blocked,
	)
	response = await client.post(
		'/users/claim-cookie',
		json={'claim_token': create_token('visitor')},
	)
	assert response.status_code == 403
	assert 'Private' not in response.text
	assert 'set-cookie' not in response.headers


@pytest.mark.parametrize('origin', ['', 'https://other.test'])
async def test_claim_rejects_untrusted_origin(
	client: httpx.AsyncClient,
	origin: str,
	user_lookup: AsyncMock,
) -> None:
	"""Require the browser's configured frontend origin."""
	response = await client.post(
		'/users/claim-cookie',
		json={'claim_token': create_token('visitor')},
		headers={'Origin': origin},
	)
	assert response.status_code == 403
	assert 'set-cookie' not in response.headers
	user_lookup.assert_not_awaited()


async def test_claim_handles_database_failure(
	client: httpx.AsyncClient,
	user_lookup: AsyncMock,
) -> None:
	"""Report service failure without leaking details."""
	user_lookup.side_effect = RuntimeError('Private URI')
	response = await client.post(
		'/users/claim-cookie',
		json={'claim_token': create_token('visitor')},
	)
	assert response.status_code == 500
	assert 'Private' not in response.text
	assert 'set-cookie' not in response.headers
