"""Check access gates before invoking memory operations."""

from datetime import timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

from authorisation.jwt.create import create_token
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit
ENDPOINTS = [
	('GET', '/agent-memory/fetch-chat-page'),
	('DELETE', '/agent-memory/delete-memory'),
]


@pytest.mark.parametrize('method, path', ENDPOINTS)
@pytest.mark.parametrize(
	'token_state', ['missing', 'bad', 'old']
)
async def test_authentication_precedes_memory_operations(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
	delete_memory: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
	method: str,
	path: str,
	token_state: str,
) -> None:
	"""Require a valid JWT before memory operations."""
	client.cookies.clear()
	if token_state == 'bad':
		client.cookies.set('JWT', 'invalid')
	elif token_state == 'old':
		monkeypatch.setattr(
			'authorisation.jwt.create.get_utc_datetime_now',
			lambda: get_utc_datetime_now() - timedelta(days=7),
		)
		client.cookies.set('JWT', create_token('visitor'))
	response = await client.request(method, path)
	assert response.status_code == 401
	retrieve_page.assert_not_awaited()
	delete_memory.assert_not_awaited()


@pytest.mark.parametrize('method, path', ENDPOINTS)
@pytest.mark.parametrize('entity', list(BlockedEntity))
async def test_blocks_precede_memory_operations(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
	delete_memory: AsyncMock,
	block_check: AsyncMock,
	method: str,
	path: str,
	entity: BlockedEntity,
) -> None:
	"""Reject blocked identities before memory operations."""

	async def enforce(target, identifier):
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
					reason='Private reason',
				)
			)

	block_check.side_effect = enforce
	response = await client.request(method, path)
	assert response.status_code == 403
	assert 'Private' not in response.text
	retrieve_page.assert_not_awaited()
	delete_memory.assert_not_awaited()


@pytest.mark.parametrize('method, path', ENDPOINTS)
@pytest.mark.parametrize('origin', ['', 'https://other.test'])
async def test_origins_precede_memory_operations(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
	delete_memory: AsyncMock,
	method: str,
	path: str,
	origin: str,
) -> None:
	"""Check origins on the agent-memory prefix."""
	response = await client.request(
		method, path, headers={'Origin': origin}
	)
	assert response.status_code == 403
	retrieve_page.assert_not_awaited()
	delete_memory.assert_not_awaited()
