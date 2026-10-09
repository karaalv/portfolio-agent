"""Check authenticated chat pages and response projection."""

from datetime import timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

from agent.config.memory import AGENT_MEMORY_PAGE_SIZE
from schemas.agent.chat import AgentChatMemory, AgentChatSource
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('offset', [None, 0, 30, 60])
async def test_fetch_passes_offset_and_serialises_messages(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
	offset: int | None,
) -> None:
	"""Scope retrieval by JWT and preserve message order."""
	now = get_utc_datetime_now()
	messages = [
		AgentChatMemory(
			memory_id='message-1',
			user_id='visitor',
			memory_source=AgentChatSource.USER,
			created_at=now - timedelta(seconds=1),
			content='Hello',
		),
		AgentChatMemory(
			memory_id='message-2',
			user_id='visitor',
			memory_source=AgentChatSource.AGENT,
			created_at=now,
			content='Hi there',
		),
	]
	retrieve_page.return_value = messages
	params = {'offset': offset} if offset is not None else {}
	response = await client.get(
		'/agent-memory/fetch-chat-page',
		params=params,
		headers={'X-Request-ID': 'memory-request'},
	)
	assert response.status_code == 200
	assert response.json()['data'] == [
		message.model_dump(mode='json') for message in messages
	]
	assert response.json()['meta']['success'] is True
	assert (
		response.json()['meta']['request_id'] == 'memory-request'
	)
	retrieve_page.assert_awaited_once_with(
		user_id='visitor', offset=offset or 0
	)


@pytest.mark.parametrize('offset', ['-1', 'invalid', '1.5'])
async def test_fetch_rejects_invalid_offset(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
	offset: str,
) -> None:
	"""Validate non-negative integer offsets before retrieval."""
	response = await client.get(
		'/agent-memory/fetch-chat-page',
		params={'offset': offset},
	)
	assert response.status_code == 422
	retrieve_page.assert_not_awaited()


async def test_fetch_pages_advance_by_visible_message_count(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
) -> None:
	"""Forward every page offset and return an empty end page."""
	all_messages = [
		AgentChatMemory(
			memory_id=f'message-{i}',
			user_id='visitor',
			memory_source=AgentChatSource.USER,
			content=str(i),
		)
		for i in range(AGENT_MEMORY_PAGE_SIZE * 2 + 1)
	]

	async def get_page(user_id: str, offset: int):
		end = len(all_messages) - offset
		start = max(0, end - AGENT_MEMORY_PAGE_SIZE)
		return all_messages[start : max(0, end)]

	retrieve_page.side_effect = get_page
	seen = []
	offset = 0
	while True:
		response = await client.get(
			'/agent-memory/fetch-chat-page',
			params={'offset': offset},
		)
		assert response.status_code == 200
		page = response.json()['data']
		if not page:
			break
		seen = page + seen
		offset += len(page)
	assert [item['memory_id'] for item in seen] == [
		item.memory_id for item in all_messages
	]
	assert offset == len(all_messages)


async def test_fetch_database_failure_is_generic(
	client: httpx.AsyncClient,
	retrieve_page: AsyncMock,
) -> None:
	"""Do not disclose internal database failure details."""
	retrieve_page.side_effect = RuntimeError('Private Mongo URI')
	response = await client.get('/agent-memory/fetch-chat-page')
	assert response.status_code == 500
	assert response.json()['meta']['success'] is False
	assert 'Private' not in response.text
