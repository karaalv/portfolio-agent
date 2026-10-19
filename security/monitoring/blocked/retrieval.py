"""Retrieve blocks whose existence denies entity access."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)


async def retrieve_block(
	entity: BlockedEntity, entity_id: str
) -> BlockedRecord | None:
	"""Return a stored block regardless of its expiry."""
	document = await get_collection(
		MongoDBCollection.BLOCKED
	).find_one({'entity': entity.value, 'entity_id': entity_id})
	if document is None:
		return None
	return BlockedRecord.model_validate(document)
