"""Build ordered agent artefacts for memory and chat tests."""

from datetime import UTC, datetime, timedelta

from agent.input_items import (
	create_assistant_input_item,
	create_function_call_item,
	create_function_output_item,
	create_user_input_item,
)
from schemas.agent.memory import AgentMemory
from shared.ids import generate_uuid_str


def make_memories(
	user_id: str,
	turns: int = 3,
) -> list[AgentMemory]:
	"""
	Build five artefacts per turn with tied BSON timestamps.
	"""
	memories: list[AgentMemory] = []
	for turn in range(turns):
		turn_id = generate_uuid_str()
		call_id = generate_uuid_str()
		payloads = [
			create_user_input_item(f'Question {turn}'),
			{
				'type': 'reasoning',
				'id': f'rs_{turn}',
				'summary': [],
			},
			create_function_call_item(
				generate_uuid_str(),
				call_id,
				'fetch_context',
				'{"user_input":"education"}',
			),
			create_function_output_item(
				call_id, 'Retrieved context'
			),
			create_assistant_input_item(f'Answer {turn}'),
		]
		for sequence, payload in enumerate(payloads):
			memories.append(
				AgentMemory(
					user_id=user_id,
					turn_id=turn_id,
					created_at=(
						datetime(2026, 10, 1, tzinfo=UTC)
						+ timedelta(minutes=turn)
					),
					sequence=sequence,
					payload=payload,
				)
			)
	return memories


def memory_documents(memories: list[AgentMemory]) -> list[dict]:
	"""
	Serialise artefacts while retaining BSON datetime values.
	"""
	documents = []
	for memory in memories:
		document = memory.model_dump(mode='json')
		document['created_at'] = memory.created_at
		documents.append(document)
	return documents
