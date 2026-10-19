"""Check deletion scoped to the authenticated visitor."""

from unittest.mock import AsyncMock

import httpx
import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('deleted', [0, 4])
async def test_delete_scopes_all_memory_to_verified_user(
	client: httpx.AsyncClient,
	delete_memory: AsyncMock,
	deleted: int,
) -> None:
	"""Succeed even when the visitor has no remaining records."""
	delete_memory.return_value = deleted
	response = await client.delete(
		'/agent-memory/delete-memory',
		params={'user_id': 'another-visitor'},
	)
	assert response.status_code == 200
	assert response.json()['meta']['success'] is True
	assert response.json()['data'] is None
	delete_memory.assert_awaited_once_with(user_id='visitor')


async def test_delete_database_failure_is_generic(
	client: httpx.AsyncClient,
	delete_memory: AsyncMock,
) -> None:
	"""Report deletion failures without leaking details."""
	delete_memory.side_effect = RuntimeError('Private Mongo URI')
	response = await client.delete('/agent-memory/delete-memory')
	assert response.status_code == 500
	assert response.json()['meta']['success'] is False
	assert 'Private' not in response.text
