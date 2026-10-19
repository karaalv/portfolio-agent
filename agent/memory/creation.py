"""Construct and persist replayable model memory items."""

from openai.types.responses import (
	ResponseInputItemParam,
	ResponseInputParam,
)

from agent.input_items import (
	create_assistant_input_item,
	create_user_input_item,
)
from agent.memory.insertion import insert_agent_memory
from agent.streaming.stream_manager import StreamManager
from schemas.agent.memory import AgentMemory


async def create_assistant_memory(
	user_id: str,
	turn_id: str,
	sequence: int,
	content: str,
) -> AgentMemory:
	"""Store a constructed assistant text item."""
	item = create_assistant_input_item(content)
	memory = AgentMemory(
		user_id=user_id,
		turn_id=turn_id,
		sequence=sequence,
		payload=item,
	)
	return await insert_agent_memory(memory)


async def create_user_memory(
	user_id: str,
	turn_id: str,
	sequence: int,
	content: str,
) -> AgentMemory:
	"""Store a visitor text item for model replay."""
	item = create_user_input_item(content)
	memory = AgentMemory(
		user_id=user_id,
		turn_id=turn_id,
		sequence=sequence,
		payload=item,
	)
	return await insert_agent_memory(memory)


async def create_response_item_memory(
	stream_manager: StreamManager,
	payload: ResponseInputItemParam,
) -> AgentMemory:
	"""Store a response item for model replay."""
	memory = AgentMemory(
		user_id=stream_manager.get_user_id(),
		turn_id=stream_manager.get_turn_id(),
		sequence=stream_manager.increment_turn_sequence_counter(),
		payload=payload,
	)
	return await insert_agent_memory(memory)


async def create_response_input_memories(
	stream_manager: StreamManager,
	payloads: ResponseInputParam,
) -> list[AgentMemory]:
	"""Persist input items sequentially in their supplied order.

	Use the same turn and allocate one sequence per item.
	Return the stored records in input order. Stop on failure
	so the caller cannot continue with unpersisted history.
	"""
	memories: list[AgentMemory] = []
	for payload in payloads:
		memories.append(
			await create_response_item_memory(
				stream_manager=stream_manager,
				payload=payload,
			)
		)
	return memories
