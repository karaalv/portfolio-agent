"""
Stream Manager class for handling
streaming operations and response state.
"""

from schemas.agent.streaming.stream_manager import (
	EventStreamState,
	StreamManagerFunctionCall,
	StreamManagerItem,
	StreamManagerItemType,
)
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, rich_print


class StreamManager:
	def __init__(self, user_id: str, verbosity_level: int = 0):
		# Session information
		self._user_id = user_id
		self._turn_id = generate_uuid_str()
		self._turn_sequence_counter: int = 0
		# Event stream state
		self._event_stream_state: EventStreamState = (
			EventStreamState.IDLE
		)
		# Stream state
		self._stream_items: list[StreamManagerItem] = []
		self._stream_sequence_counter: int = 0
		# Memory information
		self._current_memory_id: str = generate_uuid_str()
		# Function calls
		self._function_calls: dict[
			str, StreamManagerFunctionCall
		] = {}
		# Logging
		self.verbosity_level = verbosity_level

	# --- Getter Methods ---

	def get_user_id(self) -> str:
		return self._user_id

	def get_turn_id(self) -> str:
		return self._turn_id

	def get_turn_sequence_counter(self) -> int:
		return self._turn_sequence_counter

	def get_function_calls(
		self,
	) -> dict[str, StreamManagerFunctionCall]:
		return self._function_calls

	def get_current_memory_id(self) -> str:
		return self._current_memory_id

	def get_event_stream_state(self) -> EventStreamState:
		return self._event_stream_state

	# --- Setter Methods ---

	def set_function_call_state(self) -> None:
		self._event_stream_state = EventStreamState.FUNCTION_CALL

	def set_idle_state(self) -> None:
		self._event_stream_state = EventStreamState.IDLE

	def set_message_state(self) -> None:
		self._event_stream_state = EventStreamState.MESSAGE

	# --- Event Stream State Management ---

	def increment_turn_sequence_counter(self) -> int:
		current = self._turn_sequence_counter
		self._turn_sequence_counter += 1
		return current

	# --- Function Calls ---

	def has_function_calls(self) -> bool:
		return bool(self._function_calls)

	def clear_function_calls(self) -> None:
		self._function_calls.clear()

	def add_function_call(
		self,
		call_id: str,
		tool_name: str | None,
		tool_args: str = '{}',
	) -> None:
		if not call_id or not tool_name:
			return

		self._function_calls[call_id] = StreamManagerFunctionCall(
			call_id=call_id,
			tool_name=tool_name,
			tool_args=tool_args,
		)

		if self.verbosity_level > 0:
			rich_print(
				f'Added tool call\n'
				f'call_id: {call_id} \n'
				f'name {tool_name} \n'
				f'args: {tool_args}',
				style=LogStyle.INFO,
			)

	# --- Response Stream Processing ---

	def add_delta(self, delta: str) -> StreamManagerItem:
		"""
		Main method for packaging streaming deltas
		into StreamManagerItem instances for publishing
		application-level events.
		"""

		# Only text type items are currently
		# being added at this point.
		item = StreamManagerItem(
			user_id=self._user_id,
			memory_id=self.get_current_memory_id(),
			type=StreamManagerItemType.TEXT,
			sequence_number=self._increment_stream_sequence_counter(),
			payload=delta,
		)
		self._add_stream_manager_item(item)
		if self.verbosity_level > 1:
			rich_print(
				f'Added stream manager item: {item}',
				style=LogStyle.INFO,
			)
		return item

	def _add_stream_manager_item(
		self, item: StreamManagerItem
	) -> None:
		self._stream_items.append(item)

	def _increment_stream_sequence_counter(self) -> int:
		current = self._stream_sequence_counter
		self._stream_sequence_counter += 1
		return current
