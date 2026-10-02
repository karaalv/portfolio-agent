"""Delete a visitor's stored conversation history."""

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection


async def delete_agent_memory(user_id: str) -> int:
    """
    Delete matching memories without archiving,
    returning the count.
    """
    collection = get_collection(MongoDBCollection.MEMORIES)
    result = await collection.delete_many({'user_id': user_id})
    return result.deleted_count
