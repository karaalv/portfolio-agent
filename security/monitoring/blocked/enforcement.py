"""Persist new blocks and reject already blocked entities."""

from typing import NoReturn

from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import BlockedEntity
from security.monitoring.blocked.creation import create_block
from security.monitoring.blocked.retrieval import retrieve_block


async def apply_24h_block(
	entity: BlockedEntity, entity_id: str, reason: str
) -> NoReturn:
	"""Persist or reuse a block before denying access."""
	record = await create_block(entity, entity_id, reason)
	raise EntityBlockedException(record)


async def enforce_existing_block(
	entity: BlockedEntity, entity_id: str
) -> None:
	"""Reject stored blocks, including expired records."""
	record = await retrieve_block(entity, entity_id)
	if record is not None:
		raise EntityBlockedException(record)
