"""Limit application requests before checking IP blocks."""

from typing import Annotated

from fastapi import (
	Depends,
	HTTPException,
	Request,
	WebSocket,
	WebSocketException,
)

from api.dependencies.auth._checks import (
	check_entity_block,
	retrieve_application_limiter,
)
from api.utils.ratelimit import (
	acquire_http_rate_limit,
	acquire_ws_rate_limit,
)
from api.utils.requests import get_http_ip, get_ws_ip
from api.websocket.helpers.context import (
	connection_exception,
	initialise_connection_context,
)
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


async def require_ws_ip_access(websocket: WebSocket) -> str:
	"""Apply IP access checks before accepting a socket."""
	initialise_connection_context(websocket)
	try:
		ip_address = get_ws_ip(websocket)
		limiter = await retrieve_application_limiter(
			ResourceAccessor.IP, ip_address
		)
		await acquire_ws_rate_limit(limiter)
		await check_entity_block(BlockedEntity.IP, ip_address)
	except HTTPException as exc:
		raise connection_exception(
			websocket,
			1011 if exc.status_code >= 500 else 1008,
			str(exc.detail),
		) from exc
	except WebSocketException as exc:
		raise connection_exception(
			websocket, exc.code, exc.reason
		) from exc
	except Exception as exc:
		raise connection_exception(
			websocket, 1011, 'Unable to check IP access.'
		) from exc
	return ip_address


WSIPAccess = Annotated[str, Depends(require_ws_ip_access)]
