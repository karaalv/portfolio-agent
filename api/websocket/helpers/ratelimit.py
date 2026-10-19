"""Acquire user and IP allowances for an agent message."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from api.utils.ratelimit import acquire_ws_rate_limit
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.lifecycle import get_limiter


@asynccontextmanager
async def agent_message_rate_limit(
	user_id: str, ip_address: str
) -> AsyncGenerator[None]:
	"""Charge both allowances before processing one message.

	Capacity replenishes over time; leaving does not refund it.
	"""
	for accessor, identifier in (
		(ResourceAccessor.IP, ip_address),
		(ResourceAccessor.USER, user_id),
	):
		limiter = await get_limiter(
			ResourceScope.AGENT_MESSAGE, accessor, identifier
		)
		await acquire_ws_rate_limit(limiter)
	yield
