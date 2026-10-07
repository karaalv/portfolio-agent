"""Check delta packaging and function-call state in isolation."""

from uuid import UUID

import pytest

from agent.streaming.stream_manager import StreamManager
from schemas.agent.streaming.stream_manager import (
	EventStreamState,
	StreamManagerItemType,
)

pytestmark = pytest.mark.unit


def test_deltas_keep_identity_and_increase_sequence() -> None:
	"""
	Package each delta without changing memory or turn identity.
	"""
	manager = StreamManager('visitor')
	assert (
		manager.get_event_stream_state() == EventStreamState.IDLE
	)
	manager.set_message_state()
	first = manager.add_delta('Hello ')
	second = manager.add_delta('there')
	assert [first.payload, second.payload] == ['Hello ', 'there']
	assert [first.sequence_number, second.sequence_number] == [
		0,
		1,
	]
	assert first.user_id == second.user_id == 'visitor'
	assert first.memory_id == second.memory_id
	assert first.memory_id == manager.get_current_memory_id()
	assert (
		first.type == second.type == StreamManagerItemType.TEXT
	)
	assert first.stream_id != second.stream_id
	assert UUID(manager.get_turn_id()).version == 4
	assert first.timestamp.tzinfo is not None
	assert manager.increment_turn_sequence_counter() == 0
	assert manager.increment_turn_sequence_counter() == 1
	manager.set_idle_state()
	assert (
		manager.get_event_stream_state() == EventStreamState.IDLE
	)


def test_function_calls_preserve_arguments_and_order() -> None:
	"""
	Store complete raw JSON calls and clear them after a round.
	"""
	manager = StreamManager('visitor')
	manager.set_function_call_state()
	assert manager.get_event_stream_state() == (
		EventStreamState.FUNCTION_CALL
	)
	manager.add_function_call(
		'first', 'fetch_context', '{"a":1}'
	)
	manager.add_function_call(
		'second', 'fetch_context', '{"a":2}'
	)
	manager.add_function_call('', 'fetch_context')
	manager.add_function_call('missing-name', None)
	assert list(manager.get_function_calls()) == [
		'first',
		'second',
	]
	assert manager.get_function_calls()['first'].tool_args == (
		'{"a":1}'
	)
	assert manager.has_function_calls()
	manager.clear_function_calls()
	assert not manager.has_function_calls()
