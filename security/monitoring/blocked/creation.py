"""Persist a block once within the sole application process."""

import asyncio
from datetime import timedelta

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from security.monitoring.blocked.config import (
	BLOCK_DURATION_HOURS,
)
from security.monitoring.blocked.retrieval import retrieve_block
from shared.logging import log_warning
from shared.logging.context import log_properties
from shared.time import get_utc_datetime_now

_creation_lock = asyncio.Lock()


async def create_block(
	entity: BlockedEntity, entity_id: str, reason: str
) -> BlockedRecord:
	"""Reuse existing blocks without extending expiry."""
	async with _creation_lock:
		existing = await retrieve_block(entity, entity_id)
		if existing is not None:
			return existing
		now = get_utc_datetime_now()
		record = BlockedRecord(
			entity=entity,
			entity_id=entity_id,
			blocked_at=now,
			blocked_until=now + timedelta(hours=BLOCK_DURATION_HOURS),
			reason=reason,
		)
		await get_collection(MongoDBCollection.BLOCKED).insert_one(
			record.model_dump()
		)
		_log_block_created(record)
		return record


def _log_block_created(record: BlockedRecord) -> None:
	"""Log only newly persisted blocks, not repeated rejections."""
	log_warning(
		'block_applied',
		log_properties(
			'block_applied',
			user_id=record.entity_id
			if record.entity == BlockedEntity.USER
			else None,
			entity_type=record.entity.value,
			entity_id=record.entity_id,
			reason=record.reason,
			blocked_at=record.blocked_at.isoformat(),
			blocked_until=record.blocked_until.isoformat(),
		),
	)
