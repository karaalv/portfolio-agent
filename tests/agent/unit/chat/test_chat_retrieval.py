"""Check visible chat conversion and message-only pagination."""

import pytest

from agent.chat import retrieval
from schemas.agent.chat import AgentChatSource
from tests.shared.agent import make_memories, memory_documents

pytestmark = pytest.mark.unit


async def test_chat_pages_reach_all_visible_messages(
	memory_collection,
	monkeypatch,
) -> None:
	"""
	Count visible messages, excluding tool and reasoning items.
	"""
	memories = make_memories('visitor', 4)
	memory_collection.documents = memory_documents(
		memories + make_memories('other')
	)
	monkeypatch.setattr(retrieval, 'AGENT_MEMORY_PAGE_SIZE', 3)
	expected = [
		m
		for m in memories
		if m.payload.get('type') == 'message'
		and m.payload.get('role') in {'user', 'assistant'}
	]
	seen = []
	offset = 0
	while page := await retrieval.retrieve_agent_chat_page(
		'visitor', offset
	):
		assert len(page) <= 3
		assert all(m.user_id == 'visitor' for m in page)
		seen = page + seen
		offset += len(page)
	assert [m.memory_id for m in seen] == [
		m.memory_id for m in expected
	]
	expected_content = []
	for memory in expected:
		payload = memory.payload
		assert retrieval._is_chat_message(payload)
		expected_content.append(payload['content'])
	assert [m.content for m in seen] == expected_content
	assert seen[0].memory_source == AgentChatSource.USER
	assert seen[-1].memory_source == AgentChatSource.AGENT
	assert len(seen) == len({m.memory_id for m in seen})


@pytest.mark.parametrize(
	'blocks, expected',
	[
		([{'type': 'input_text', 'text': 'Hello'}], 'Hello'),
		(
			[
				{
					'type': 'output_text',
					'text': 'First',
					'annotations': [],
				},
				{
					'type': 'output_text',
					'text': ' second',
					'annotations': [],
				},
			],
			'First second',
		),
		(
			[{'type': 'refusal', 'refusal': 'Cannot comply'}],
			'Cannot comply',
		),
	],
)
def test_chat_conversion_handles_content_blocks(
	blocks, expected
):
	"""
	Render text blocks and refusals in their original order.
	"""
	memory = make_memories('visitor', 1)[-1]
	memory.payload = {
		'type': 'message',
		'role': 'assistant',
		'content': blocks,
	}
	result = retrieval._to_agent_chat_memory(memory)
	assert result.content == expected
	assert result.created_at == memory.created_at
	assert result.memory_id == memory.memory_id


def test_non_message_cannot_be_rendered() -> None:
	"""Reject a tool output instead of leaking internal text."""
	with pytest.raises(ValueError, match='chat message'):
		retrieval._to_agent_chat_memory(
			make_memories('visitor')[3]
		)


async def test_empty_and_invalid_chat_pages(memory_collection):
	"""Return an empty page and reject a negative offset."""
	assert (
		await retrieval.retrieve_agent_chat_page('visitor', 0)
		== []
	)
	with pytest.raises(ValueError, match='offset'):
		await retrieval.retrieve_agent_chat_page('visitor', -1)
