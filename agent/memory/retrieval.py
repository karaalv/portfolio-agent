"""
Retrieve user-scoped conversation records and prompt context.
"""

from agent.config.memory import (
	AGENT_MEMORY_LIMIT,
	AGENT_MEMORY_PAGE_SIZE,
)
from agent.prompts.memory import format_agent_memory_prompt
from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.memory import AgentMemory


async def retrieve_agent_memory(
	user_id: str, limit: int | None = None
) -> list[AgentMemory]:
	"""
	Return chronological history,
	optionally limited to recent entries.
	"""
	if limit is not None and limit < 1:
		raise ValueError('The memory limit must be positive.')

	collection = get_collection(MongoDBCollection.MEMORIES)
	cursor = collection.find({'user_id': user_id}, {'_id': 0}).sort(
		[('created_at', -1), ('_id', -1)]
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


async def retrieve_agent_memory_page(
	user_id: str, offset: int
) -> list[AgentMemory]:
	"""
	Return the next page of memories in chronological order.

	Offset counts records already fetched, starting from the
	newest memory. Older pages should be prepended to the chat.
	Return an empty list when no further records are available.
	"""
	if offset < 0:
		raise ValueError('The memory offset must not be negative.')

	collection = get_collection(MongoDBCollection.MEMORIES)
	cursor = (
		collection.find({'user_id': user_id}, {'_id': 0})
		.sort([('created_at', -1), ('_id', -1)])
		.skip(offset)
		.limit(AGENT_MEMORY_PAGE_SIZE)
	)
	memories = [
		AgentMemory.model_validate(document)
		async for document in cursor
	]
	memories.reverse()
	return memories


async def retrieve_agent_memory_prompt(user_id: str) -> str:
	"""
	Fetch the configured recent history
	and format it for the agent.
	"""
	memories = await retrieve_agent_memory(
		user_id, limit=AGENT_MEMORY_LIMIT
	)
	return format_agent_memory_prompt(memories)
