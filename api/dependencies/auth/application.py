"""Enforce user blocks and limits after token authentication."""

from typing import Annotated

from fastapi import Depends

from api.dependencies.auth._checks import (
	check_entity_block,
	retrieve_application_limiter,
)
from api.dependencies.auth.access_token import AccessUserId
from api.utils.ratelimit import acquire_http_rate_limit
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.ratelimit import ResourceAccessor


async def require_application_access(
	user_id: AccessUserId,
) -> str:
	"""Reject user blocks and acquire the user's allowance."""
	await check_entity_block(BlockedEntity.USER, user_id)
	limiter = await retrieve_application_limiter(
		ResourceAccessor.USER, user_id
	)
	await acquire_http_rate_limit(limiter)
	return user_id


ApplicationUserId = Annotated[
	str, Depends(require_application_access)
]
