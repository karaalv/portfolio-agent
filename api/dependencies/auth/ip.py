"""Limit application requests before checking IP blocks."""

from typing import Annotated

from fastapi import Depends, Request

from api.dependencies.auth._checks import (
	check_entity_block,
	retrieve_application_limiter,
)
from api.utils.ratelimit import acquire_http_rate_limit
from api.utils.requests import get_http_ip
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.ratelimit import ResourceAccessor


async def require_ip_access(request: Request) -> str:
	"""Acquire IP capacity and reject a stored IP block."""
	ip_address = get_http_ip(request)
	limiter = await retrieve_application_limiter(
		ResourceAccessor.IP, ip_address
	)
	await acquire_http_rate_limit(limiter)
	await check_entity_block(BlockedEntity.IP, ip_address)
	return ip_address


IPAccess = Annotated[str, Depends(require_ip_access)]
