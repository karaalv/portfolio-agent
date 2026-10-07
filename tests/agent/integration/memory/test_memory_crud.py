"""Exercise memory creation, BSON persistence and deletion."""

from datetime import datetime

import pytest
from openai.types.responses import ResponseInputParam

from agent.input_items import create_function_output_item
from agent.memory.creation import (
	create_assistant_memory,
	create_response_input_memories,
	create_user_memory,
)
from agent.memory.deletion import delete_agent_memory
from agent.memory.retrieval import retrieve_agent_memory
from agent.streaming.stream_manager import StreamManager
from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from agent.chat import retrieval

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_memory_creation_and_deletion(
	user_id,
	other_user_id,
) -> None:
	"""
	Round-trip messages and delete only their owning visitor.
	"""
	user = await create_user_memory(user_id, 'turn', 0, 'Hello')
	assistant = await create_assistant_memory(
		user_id, 'turn', 1, 'Welcome'
	)
	await create_user_memory(
		other_user_id, 'other-turn', 0, 'Other'
	)
	memories = await retrieve_agent_memory(user_id, None)
	assert [m.memory_id for m in memories] == [
		user.memory_id,
		assistant.memory_id,
	]
	memory_result = []
	for m in memories:
		assert retrieval._is_chat_message(m.payload)
		memory_result.append(m.payload['content'])
	assert memory_result == [
		'Hello',
		'Welcome',
	]
	assert all(m.created_at.tzinfo is not None for m in memories)
	collection = get_collection(MongoDBCollection.MEMORIES)
	raw = await collection.find_one(
		{'memory_id': user.memory_id}
	)
	assert raw is not None
	assert isinstance(raw['created_at'], datetime)
	assert raw['payload'] == user.payload
	assert await delete_agent_memory(user_id) == 2
	assert await retrieve_agent_memory(user_id, None) == []
	assert await delete_agent_memory(user_id) == 0
	assert (
		len(await retrieve_agent_memory(other_user_id, None))
		== 1
	)


async def test_response_outputs_keep_sequence(user_id) -> None:
	"""
	Persist ordered tool outputs with one turn and unique IDs.
	"""
	manager = StreamManager(user_id)
	payloads: ResponseInputParam = [
		create_function_output_item('first', 'One'),
		create_function_output_item('second', 'Two'),
	]
	stored = await create_response_input_memories(
		manager, payloads
	)
	memories = await retrieve_agent_memory(user_id, None)
	assert [m.memory_id for m in memories] == [
		m.memory_id for m in stored
	]
	assert [m.payload for m in memories] == payloads
	assert [m.sequence for m in memories] == [0, 1]
	assert {m.turn_id for m in memories} == {
		manager.get_turn_id()
	}
	assert len({m.memory_id for m in memories}) == 2
