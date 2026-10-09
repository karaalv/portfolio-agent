"""Own the rate-limit store within the sole app process."""

from aiolimiter import AsyncLimiter

from exceptions.security import SecurityServiceException
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.ratelimit import RateLimitStore
from shared.logging import LogStyle, rich_print

_security_client: RateLimitStore | None = None


async def start_security_client() -> None:
	"""Create the store once on the running event loop."""
	if _security_client is not None:
		return
	set_security_client(RateLimitStore())
	rich_print(
		'Security client started.',
		style=LogStyle.SUCCESS,
		prefix='security.lifecycle',
	)


async def stop_security_client() -> None:
	"""Stop cleanup before clearing the client reference."""
	if _security_client is None:
		return
	await _security_client.stop()
	set_security_client(None)
	rich_print(
		'Security client stopped.',
		style=LogStyle.SUCCESS,
		prefix='security.lifecycle',
	)


def get_security_client() -> RateLimitStore:
	"""Return the started store or raise a service error."""
	if _security_client is None:
		raise SecurityServiceException(
			'Security client is not started.',
			operation='get_security_client',
		)
	return _security_client


def set_security_client(client: RateLimitStore | None) -> None:
	"""Replace the reference without stopping the old store."""
	global _security_client
	_security_client = client


async def get_limiter(
	resource_scope: ResourceScope,
	resource_accessor: ResourceAccessor,
	identifier_value: str,
) -> AsyncLimiter:
	"""Fetch an allowance from the started security store."""
	return await get_security_client().get_limiter(
		resource_scope, resource_accessor, identifier_value
	)
