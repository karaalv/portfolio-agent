"""Update activity timestamps for anonymous users."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from shared.time import get_utc_datetime_now


async def update_last_active(user_id: str) -> bool:
	"""Set UTC activity; return whether a record changed."""
	collection = get_collection(MongoDBCollection.USERS)
	result = await collection.update_one(
		{'user_id': user_id},
		{'$set': {'last_active_at': get_utc_datetime_now()}},
	)
	return result.modified_count > 0
