"""Delete all stored model artefacts belonging to a visitor."""

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection


async def delete_agent_memory(user_id: str) -> int:
	"""
	Delete messages, tool items and reasoning for one visitor.
	Return the number of deleted memory records.
	"""
	collection = get_collection(MongoDBCollection.MEMORIES)
	result = await collection.delete_many({'user_id': user_id})
	return result.deleted_count
