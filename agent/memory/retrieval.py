"""
Retrieve stored API items for model conversation history.
"""

from openai.types.responses import ResponseInputParam

from agent.config.memory import (
	AGENT_MEMORY_LIMIT,
	AGENT_MEMORY_PAGE_SIZE,
)
from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.memory import AgentMemory


async def retrieve_agent_memory(
	user_id: str, limit: int | None = AGENT_MEMORY_LIMIT
) -> list[AgentMemory]:
	"""
	Return stored artefacts, including tools and reasoning,
	optionally limited to recent entries in chronological order.
	"""
	if limit is not None and limit < 1:
		raise ValueError('The memory limit must be positive.')

	# - Fetch memories from database -
	collection = get_collection(MongoDBCollection.MEMORIES)
	cursor = collection.find({'user_id': user_id}, {'_id': 0}).sort(
		[('created_at', -1), ('sequence', -1)]
	)
	if limit is not None:
		cursor = cursor.limit(limit)
	memories = [
		AgentMemory.model_validate(document)
		async for document in cursor
	]
	# Reverse to chronological order
	memories.reverse()
	return memories


async def retrieve_agent_memory_param(
	user_id: str, limit: int | None = AGENT_MEMORY_LIMIT
) -> ResponseInputParam:
	"""Return stored payloads ready for the model input field."""
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
		raise ValueError('The memory offset must not be negative.')

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
