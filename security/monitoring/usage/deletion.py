"""Delete usage records independently of application users."""

from datetime import timedelta

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.usage import UsageEntity
from security.monitoring.usage.config import USAGE_RETENTION_DAYS
from shared.time import get_utc_datetime_now


async def delete_usage_statistics(
	entity: UsageEntity, entity_id: str
) -> int:
	"""Delete matching usage records and report their count."""
	result = await get_collection(
		MongoDBCollection.USAGE
	).delete_many(
		{'entity': entity.value, 'entity_id': entity_id}
	)
	return result.deleted_count


async def prune_inactive_usage() -> int:
	"""Delete inactive records; socket cleanup comes later."""
	cutoff = get_utc_datetime_now() - timedelta(
		days=USAGE_RETENTION_DAYS
	)
	result = await get_collection(
		MongoDBCollection.USAGE
	).delete_many({'last_request_at': {'$lt': cutoff}})
	return result.deleted_count
