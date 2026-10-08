"""Create usage records explicitly before recording activity."""

import asyncio

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.usage import (
	UsageEntity,
	UsageStatistics,
)
from security.monitoring.usage.retrieval import (
	retrieve_usage_statistics,
)

_creation_lock = asyncio.Lock()


async def create_usage_statistics(
	entity: UsageEntity, entity_id: str
) -> UsageStatistics:
	"""Create once within the single application process."""
	async with _creation_lock:
		existing = await retrieve_usage_statistics(
			entity, entity_id
		)
		if existing is not None:
			return existing
		statistics = UsageStatistics(
			entity=entity, entity_id=entity_id
		)
		await get_collection(MongoDBCollection.USAGE).insert_one(
			statistics.model_dump()
		)
		return statistics
