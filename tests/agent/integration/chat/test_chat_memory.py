"""
Read visible chat records from the shared memory collection.
"""

import pytest

from agent.chat.retrieval import (
	_is_chat_message,
	retrieve_agent_chat_page,
)
from agent.memory.creation import (
	create_assistant_memory,
	create_user_memory,
)
from agent.memory.deletion import delete_agent_memory
from agent.memory.insertion import insert_agent_memory
from schemas.agent.chat import AgentChatMemory, AgentChatSource
from schemas.agent.memory import AgentMemory
from tests.shared.agent import make_memories

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_chat_creation_retrieval_and_deletion(
	user_id,
	other_user_id,
) -> None:
	"""
	Display stored messages and reflect owner-scoped deletion.
	"""
	assert await retrieve_agent_chat_page(user_id, 0) == []
	await create_user_memory(user_id, 'turn', 0, 'Hello')
	await create_assistant_memory(user_id, 'turn', 1, 'Welcome')
	await create_user_memory(other_user_id, 'turn', 0, 'Other')
	page = await retrieve_agent_chat_page(user_id, 0)
	assert all(isinstance(m, AgentChatMemory) for m in page)
	assert [m.content for m in page] == ['Hello', 'Welcome']
	assert [m.memory_source for m in page] == [
		AgentChatSource.USER,
		AgentChatSource.AGENT,
	]
	assert await delete_agent_memory(user_id) == 2
	assert await retrieve_agent_chat_page(user_id, 0) == []
	assert (
		len(await retrieve_agent_chat_page(other_user_id, 0))
		== 1
	)


async def test_chat_pagination_reaches_all_messages(
	user_id,
	other_user_id,
) -> None:
	"""
	Page visible messages without counting internal artefacts.
	"""
	memories = make_memories(user_id, 17)
	for memory in memories + make_memories(other_user_id, 1):
		await insert_agent_memory(memory)
	expected = [
		m
		for m in memories
		if m.payload.get('type') == 'message'
		and m.payload.get('role') in {'user', 'assistant'}
	]
	seen = []
	offset = 0
	while page := await retrieve_agent_chat_page(
		user_id, offset
	):
		assert all(m.user_id == user_id for m in page)
		seen = page + seen
		offset += len(page)
	assert [m.memory_id for m in seen] == [
		m.memory_id for m in expected
	]
	expected_content = []
	for memory in expected:
		payload = memory.payload
		assert _is_chat_message(payload)
		expected_content.append(payload['content'])
	assert [m.content for m in seen] == expected_content
	assert len(seen) == len({m.memory_id for m in seen})


async def test_chat_renders_completed_output_blocks(user_id):
	"""Convert stored SDK output text into frontend content."""
	memory = make_memories(user_id, 1)[-1]
	document = memory.model_dump(mode='json')
	document['payload'] = {
		'type': 'message',
		'role': 'assistant',
		'id': 'msg_test',
		'status': 'completed',
		'content': [
			{
				'type': 'output_text',
				'text': 'Hello ',
				'annotations': [],
			},
			{
				'type': 'output_text',
				'text': 'visitor',
				'annotations': [],
			},
		],
	}
	memory = AgentMemory.model_validate(document)
	await insert_agent_memory(memory)
	page = await retrieve_agent_chat_page(user_id, 0)
	assert len(page) == 1
	assert page[0].content == 'Hello visitor'
	assert page[0].memory_id == memory.memory_id
