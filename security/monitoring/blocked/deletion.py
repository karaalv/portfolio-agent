"""Remove access blocks explicitly or after their expiry."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.blocked import BlockedEntity
from shared.time import get_utc_datetime_now


async def delete_blocks(
	entity: BlockedEntity, entity_id: str
) -> int:
	"""Remove all matching records, including any duplicates."""
	result = await get_collection(
		MongoDBCollection.BLOCKED
	).delete_many(
		{'entity': entity.value, 'entity_id': entity_id}
	)
	return result.deleted_count


async def prune_expired_blocks() -> int:
	"""Delete records eligible for expiry cleanup."""
	result = await get_collection(
		MongoDBCollection.BLOCKED
	).delete_many(
		{'blocked_until': {'$lte': get_utc_datetime_now()}}
	)
	return result.deleted_count
