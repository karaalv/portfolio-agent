"""Check real MongoDB turn boundaries and pagination coverage."""

import pytest
from openai.types.responses import ResponseInputParam
from pydantic import TypeAdapter

from agent.memory.insertion import insert_agent_memory
from agent.memory.retrieval import (
	retrieve_agent_memory,
	retrieve_agent_memory_page,
	retrieve_agent_memory_page_param,
	retrieve_agent_memory_param,
)
from tests.shared.agent import make_memories

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_history_boundary_keeps_complete_turns(
	user_id,
	other_user_id,
) -> None:
	"""
	Keep twenty turns by default, not twenty artefact records.
	"""
	memories = make_memories(user_id, 23)
	for memory in memories + make_memories(other_user_id, 1):
		await insert_agent_memory(memory)
	default = await retrieve_agent_memory(user_id)
	assert [m.memory_id for m in default] == [
		m.memory_id for m in memories[15:]
	]
	recent = await retrieve_agent_memory(user_id, 2)
	assert [m.memory_id for m in recent] == [
		m.memory_id for m in memories[-10:]
	]
	payloads = await retrieve_agent_memory_param(user_id, 2)
	assert TypeAdapter(ResponseInputParam).dump_python(
		payloads, mode='json'
	) == [m.model_dump(mode='json')['payload'] for m in recent]


async def test_memory_pagination_reaches_all_records(
	user_id,
	other_user_id,
) -> None:
	"""
	Visit every artefact across a full page and a partial page.
	"""
	memories = make_memories(user_id, 7)
	for memory in memories + make_memories(other_user_id, 1):
		await insert_agent_memory(memory)
	seen = []
	offset = 0
	while page := await retrieve_agent_memory_page(
		user_id, offset
	):
		assert [
			(m.created_at, m.sequence) for m in page
		] == sorted((m.created_at, m.sequence) for m in page)
		assert all(m.user_id == user_id for m in page)
		seen = page + seen
		offset += len(page)
	assert [m.memory_id for m in seen] == [
		m.memory_id for m in memories
	]
	assert len(seen) == len({m.memory_id for m in seen})
	assert (
		await retrieve_agent_memory_page_param(user_id, offset)
		== []
	)


async def test_empty_and_short_history(user_id) -> None:
	"""Handle a new visitor and fewer turns than the limit."""
	assert await retrieve_agent_memory(user_id) == []
	memories = make_memories(user_id, 1)
	for memory in memories:
		await insert_agent_memory(memory)
	assert len(await retrieve_agent_memory(user_id)) == 5
