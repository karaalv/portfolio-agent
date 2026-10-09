"""Check cookie claiming without external services."""

from datetime import timedelta
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest

from authorisation.jwt.create import create_token
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


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
