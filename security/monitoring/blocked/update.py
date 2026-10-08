"""Support explicit corrections to stored block reasons."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.blocked import BlockedEntity


async def update_block_reason(
	entity: BlockedEntity, entity_id: str, reason: str
) -> bool:
	"""Correct a reason without changing the blocking period."""
	if not reason.strip():
		raise ValueError('reason must not be empty.')
	result = await get_collection(
		MongoDBCollection.BLOCKED
	).update_many(
		{'entity': entity.value, 'entity_id': entity_id},
		{'$set': {'reason': reason}},
	)
	return result.modified_count > 0
