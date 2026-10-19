"""
Retrieve stored API items for model conversation history.
"""

from openai.types.responses import ResponseInputParam

from agent.config.memory import (
	AGENT_HISTORY_TURN_LIMIT,
	AGENT_MEMORY_PAGE_SIZE,
)
from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.memory import AgentMemory


async def retrieve_agent_memory(
	user_id: str, limit: int | None = AGENT_HISTORY_TURN_LIMIT
) -> list[AgentMemory]:
	"""Return history from the oldest selected user turn onwards.

	The limit counts user messages, not individual artefacts.
	Include all artefacts at or after the boundary timestamp,
	ordered by creation time and sequence. With fewer user
	messages, start at the earliest available user message.
	Pass None to retrieve the user's entire stored history.
	"""
	if limit is not None and limit < 1:
		raise ValueError('History turn limit must be positive.')

	collection = get_collection(MongoDBCollection.MEMORIES)
	query: dict[str, object] = {'user_id': user_id}
	if limit is not None:
		user_cursor = (
			collection.find(
				{
					'user_id': user_id,
					'payload.role': {'$in': ['user']},
				},
				{'_id': 0, 'created_at': 1},
			)
			.sort([('created_at', -1), ('sequence', -1)])
			.limit(limit)
		)
		async with user_cursor:
			messages = await user_cursor.to_list(length=None)
		if not messages:
			return []
		boundary = messages[-1]['created_at']
		query['created_at'] = {'$gte': boundary}

	cursor = collection.find(query, {'_id': 0}).sort(
		[('created_at', 1), ('sequence', 1)]
	)
	async with cursor:
		return [
			AgentMemory.model_validate(document)
			async for document in cursor
		]


async def retrieve_agent_memory_param(
	user_id: str, limit: int | None = AGENT_HISTORY_TURN_LIMIT
) -> ResponseInputParam:
	"""Return turn-bounded history as model input payloads."""
	memories = await retrieve_agent_memory(user_id, limit)

	# - Format memories for agent input -
	return [m.payload for m in memories]


async def retrieve_agent_memory_page(
	user_id: str, offset: int
) -> list[AgentMemory]:
	"""
	Return the next page of memories in chronological order.

	Offset counts records already fetched, starting from the
	newest memory. Offset counts all artefacts, including
	internal items.
	Use agent.chat.retrieval for frontend message pagination.
	Return an empty list when no further records are available.
	"""
	if offset < 0:
		raise ValueError('Memory offset must not be negative.')

	collection = get_collection(MongoDBCollection.MEMORIES)
	cursor = (
		collection.find({'user_id': user_id}, {'_id': 0})
		.sort([('created_at', -1), ('sequence', -1)])
		.skip(offset)
		.limit(AGENT_MEMORY_PAGE_SIZE)
	)
	memories = [
		AgentMemory.model_validate(document)
		async for document in cursor
	]
	memories.reverse()
	return memories


async def retrieve_agent_memory_page_param(
	user_id: str, offset: int
) -> ResponseInputParam:
	"""Return one artefact page as model input payloads."""
	memories = await retrieve_agent_memory_page(user_id, offset)
	return [m.payload for m in memories]
