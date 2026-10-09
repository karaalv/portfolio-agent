"""Fetch persisted chat pages and delete their owner's data."""

from datetime import timedelta

import httpx
import pytest
from pymongo.asynchronous.collection import AsyncCollection

from agent.config.memory import AGENT_MEMORY_PAGE_SIZE
from agent.memory.insertion import insert_agent_memory
from schemas.agent.chat import AgentChatMemory, AgentChatSource
from tests.shared.agent import make_memories

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_fetch_returns_visible_chat_structure(
	client: httpx.AsyncClient,
	user_id: str,
	other_user_id: str,
) -> None:
	"""Render stored messages without internal artefacts."""
	memories = make_memories(user_id, 1)
	for memory in memories + make_memories(other_user_id, 1):
		await insert_agent_memory(memory)
	response = await client.get(
		'/agent-memory/fetch-chat-page',
		headers={'X-Request-ID': 'live-memory-fetch'},
	)
	assert response.status_code == 200
	body = response.json()
	assert set(body) == {'meta', 'data'}
	assert body['meta']['success'] is True
	assert body['meta']['request_id'] == 'live-memory-fetch'
	items = body['data']
	assert len(items) == 2
	assert all(
		set(item)
		== {
			'memory_id',
			'user_id',
			'memory_source',
			'created_at',
			'content',
		}
		for item in items
	)
	parsed = [
		AgentChatMemory.model_validate(item) for item in items
	]
	assert [item.memory_id for item in parsed] == [
		memories[0].memory_id,
		memories[-1].memory_id,
	]
	assert [item.memory_source for item in parsed] == [
		AgentChatSource.USER,
		AgentChatSource.AGENT,
	]
	assert all(item.user_id == user_id for item in parsed)
	assert all(
		item.created_at.utcoffset() == timedelta(0)
		for item in parsed
	)
	assert [item.content for item in parsed] == [
		'Question 0',
		'Answer 0',
	]


async def test_fetch_pagination_reaches_all_visible_records(
	client: httpx.AsyncClient,
	user_id: str,
	other_user_id: str,
) -> None:
	"""Page chat messages without gaps or owner leakage."""
	memories = make_memories(user_id, AGENT_MEMORY_PAGE_SIZE + 1)
	for memory in memories + make_memories(other_user_id, 1):
		await insert_agent_memory(memory)
	expected = [
		memory.memory_id
		for memory in memories
		if memory.payload.get('type') == 'message'
		and memory.payload.get('role') in {'user', 'assistant'}
	]
	seen = []
	offset = 0
	for _ in range(4):
		response = await client.get(
			'/agent-memory/fetch-chat-page',
			params={'offset': offset},
		)
		assert response.status_code == 200
		page = response.json()['data']
		if not page:
			break
		assert len(page) <= AGENT_MEMORY_PAGE_SIZE
		assert all(item['user_id'] == user_id for item in page)
		seen = page + seen
		offset += len(page)
	else:
		pytest.fail('Pagination did not reach the end.')
	assert [item['memory_id'] for item in seen] == expected
	assert len({item['memory_id'] for item in seen}) == len(seen)


async def test_delete_removes_all_artefacts_for_verified_user(
	client: httpx.AsyncClient,
	memory_collection: AsyncCollection,
	user_id: str,
	other_user_id: str,
) -> None:
	"""Delete one owner's artefacts and preserve the other's."""
	memories = make_memories(user_id, 1)
	other_memories = make_memories(other_user_id, 1)
	for memory in memories + other_memories:
		await insert_agent_memory(memory)
	assert await memory_collection.count_documents(
		{'user_id': user_id}
	) == len(memories)
	response = await client.delete(
		'/agent-memory/delete-memory',
		params={'user_id': other_user_id},
	)
	assert response.status_code == 200
	body = response.json()
	assert body['meta']['success'] is True
	assert body['data'] is None
	assert (
		await memory_collection.count_documents(
			{'user_id': user_id}
		)
		== 0
	)
	assert await memory_collection.count_documents(
		{'user_id': other_user_id}
	) == len(other_memories)
	page = await client.get('/agent-memory/fetch-chat-page')
	assert page.status_code == 200
	assert page.json()['data'] == []
	second_delete = await client.delete(
		'/agent-memory/delete-memory'
	)
	assert second_delete.status_code == 200
	assert second_delete.json()['data'] is None
