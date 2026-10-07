"""Check memory persistence, creation and scoped deletion."""

from datetime import datetime

import pytest
from openai.types.responses import ResponseInputParam

from agent.input_items import create_function_output_item
from agent.memory import creation, deletion, insertion
from agent.streaming.stream_manager import StreamManager
from tests.shared.agent import make_memories, memory_documents

pytestmark = pytest.mark.unit


async def test_insertion_keeps_bson_timestamp(
	memory_collection,
) -> None:
	"""Persist a replay payload with a real datetime value."""
	memory = make_memories('visitor', 1)[0]
	assert await insertion.insert_agent_memory(memory) is memory
	document = memory_collection.insert_one.await_args.args[0]
	assert isinstance(document['created_at'], datetime)
	assert document['created_at'] == memory.created_at
	assert document['payload'] == memory.payload
	assert document['memory_id'] == memory.memory_id


@pytest.mark.parametrize('role', ['user', 'assistant'])
async def test_creation_packages_message(
	role, memory_collection
):
	"""
	Construct a message with the supplied turn and sequence.
	"""
	create = (
		creation.create_user_memory
		if role == 'user'
		else creation.create_assistant_memory
	)
	memory = await create('visitor', 'turn', 3, 'Hello')
	assert memory.payload == {
		'type': 'message',
		'role': role,
		'content': 'Hello',
	}
	assert memory.user_id == 'visitor'
	assert memory.turn_id == 'turn'
	assert memory.sequence == 3
	memory_collection.insert_one.assert_awaited_once()


async def test_response_items_share_turn_and_sequence(
	memory_collection,
) -> None:
	"""
	Persist recursion outputs in supplied order with unique IDs.
	"""
	manager = StreamManager('visitor')
	assert manager.increment_turn_sequence_counter() == 0
	payloads: ResponseInputParam = [
		create_function_output_item('call-1', 'one'),
		create_function_output_item('call-2', 'two'),
	]
	memories = await creation.create_response_input_memories(
		manager, payloads
	)
	assert [memory.sequence for memory in memories] == [1, 2]
	assert [memory.payload for memory in memories] == payloads
	assert {memory.turn_id for memory in memories} == {
		manager.get_turn_id()
	}
	assert len({memory.memory_id for memory in memories}) == 2
	assert memory_collection.insert_one.await_count == 2


async def test_response_upload_stops_on_failure(
	memory_collection,
) -> None:
	"""Do not persist later outputs after a failed insertion."""
	memory_collection.insert_one.side_effect = [
		None,
		RuntimeError('write failed'),
		None,
	]
	payloads: ResponseInputParam = [
		create_function_output_item(str(i), 'x')
		for i in range(3)
	]
	with pytest.raises(RuntimeError, match='write failed'):
		await creation.create_response_input_memories(
			StreamManager('visitor'), payloads
		)
	assert memory_collection.insert_one.await_count == 2


async def test_deletion_is_scoped_and_reports_count(
	memory_collection,
) -> None:
	"""
	Delete one visitor's artefacts without touching another.
	"""
	memory_collection.documents = memory_documents(
		make_memories('visitor') + make_memories('other', 1)
	)
	assert await deletion.delete_agent_memory('visitor') == 15
	assert await deletion.delete_agent_memory('visitor') == 0
	assert len(memory_collection.documents) == 5
	memory_collection.delete_many.assert_awaited_with(
		{'user_id': 'visitor'}
	)
