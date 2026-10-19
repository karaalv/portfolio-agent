"""Delete anonymous user records."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection


async def delete_user(user_id: str) -> bool:
	"""Delete a user; return whether a record was removed."""
	collection = get_collection(MongoDBCollection.USERS)
	result = await collection.delete_one({'user_id': user_id})
	return result.deleted_count > 0
