"""Persist replayable API items with their memory metadata."""

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.memory import AgentMemory


async def insert_agent_memory(
	memory: AgentMemory,
) -> AgentMemory:
	"""Store a payload while preserving its BSON timestamp."""
	collection = get_collection(MongoDBCollection.MEMORIES)
	document = memory.model_dump(mode='json')
	document['created_at'] = memory.created_at
	await collection.insert_one(document)
	return memory
