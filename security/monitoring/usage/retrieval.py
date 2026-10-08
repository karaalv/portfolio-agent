"""Retrieve the current counters for an entity identity."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.usage import (
	UsageEntity,
	UsageStatistics,
)


async def retrieve_usage_statistics(
	entity: UsageEntity, entity_id: str
) -> UsageStatistics | None:
	"""Return an entity's usage record, if present."""
	document = await get_collection(
		MongoDBCollection.USAGE
	).find_one({'entity': entity.value, 'entity_id': entity_id})
	if document is None:
		return None
	return UsageStatistics.model_validate(document)
