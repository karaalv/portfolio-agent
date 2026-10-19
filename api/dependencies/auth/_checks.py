"""Translate security failures into HTTP access errors."""

from aiolimiter import AsyncLimiter
from fastapi import HTTPException, status

from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.lifecycle import get_limiter
from security.monitoring.blocked.enforcement import (
	enforce_existing_block,
)


async def check_entity_block(
	entity: BlockedEntity, entity_id: str
) -> None:
	"""Reject blocks without exposing internal reasons."""
	try:
		await enforce_existing_block(entity, entity_id)
	except EntityBlockedException as exc:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail='Access is blocked.',
		) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail='Unable to check access.',
		) from exc


async def retrieve_application_limiter(
	accessor: ResourceAccessor, identifier: str
) -> AsyncLimiter:
	"""Retrieve an allowance or report unavailable security."""
	try:
		return await get_limiter(
			ResourceScope.APPLICATION, accessor, identifier
		)
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail='Unable to check rate limits.',
		) from exc
