"""Check complete history boundaries and artefact pagination."""

import pytest
from openai.types.responses import ResponseInputParam
from pydantic import TypeAdapter

from agent.memory import retrieval
from tests.shared.agent import make_memories, memory_documents

pytestmark = pytest.mark.unit


async def test_history_keeps_all_selected_turn_artefacts(
	memory_collection,
) -> None:
	"""
	A two-turn limit must return ten complete ordered records.
	"""
	memories = make_memories('visitor', 3)
	memory_collection.documents = memory_documents(
		memories + make_memories('other')
	)
	result = await retrieval.retrieve_agent_memory('visitor', 2)
	assert [m.memory_id for m in result] == [
		m.memory_id for m in memories[5:]
	]
	assert memory_collection.queries == [
		{
			'user_id': 'visitor',
			'payload.role': {'$in': ['user']},
		},
		{
			'user_id': 'visitor',
			'created_at': {
				'$gte': memories[5].created_at,
			},
		},
	]
	payloads = await retrieval.retrieve_agent_memory_param(
		'visitor', 2
	)
	assert TypeAdapter(ResponseInputParam).dump_python(
		payloads, mode='json'
	) == [m.model_dump(mode='json')['payload'] for m in result]


async def test_short_empty_and_unlimited_history(
	memory_collection,
) -> None:
	"""
	Handle fewer turns than requested and an absent visitor.
	"""
	memories = make_memories('visitor', 1)
	memory_collection.documents = memory_documents(memories)
	for limit in (20, None):
		result = await retrieval.retrieve_agent_memory(
			'visitor', limit
		)
		assert [m.memory_id for m in result] == [
			m.memory_id for m in memories
		]
	assert await retrieval.retrieve_agent_memory('absent') == []


async def test_pages_reach_every_artefact(
	memory_collection,
	monkeypatch,
) -> None:
	"""
	Advance offsets across ties without duplicates or omissions.
	"""
	memories = make_memories('visitor', 3)
	memory_collection.documents = memory_documents(
		memories + make_memories('other')
	)
	monkeypatch.setattr(retrieval, 'AGENT_MEMORY_PAGE_SIZE', 4)
	seen: list[str] = []
	offset = 0
	while page := await retrieval.retrieve_agent_memory_page(
		'visitor', offset
	):
		assert len(page) <= 4
		assert [
			(m.created_at, m.sequence) for m in page
		] == sorted((m.created_at, m.sequence) for m in page)
		seen = [m.memory_id for m in page] + seen
		offset += len(page)
	assert seen == [m.memory_id for m in memories]
	assert len(seen) == len(set(seen))
	assert (
		await retrieval.retrieve_agent_memory_page_param(
			'visitor', len(memories)
		)
		== []
	)


@pytest.mark.parametrize('limit', [0, -1])
async def test_invalid_limit_does_not_query(
	limit,
	memory_collection,
) -> None:
	"""Reject non-positive turn limits before database access."""
	with pytest.raises(ValueError, match='limit'):
		await retrieval.retrieve_agent_memory('visitor', limit)
	assert not memory_collection.queries


async def test_invalid_offset_does_not_query(
	memory_collection,
) -> None:
	"""
	Reject negative pagination offsets before database access.
	"""
	with pytest.raises(ValueError, match='offset'):
		await retrieval.retrieve_agent_memory_page('visitor', -1)
	assert not memory_collection.queries
