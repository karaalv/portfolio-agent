"""Report connection failures and finish transport cleanup once."""

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from api.websocket import get_websocket_registry
from exceptions.websocket import (
	WebSocketConnectionException,
	WebSocketRegistryException,
)
from posthog_client.error_tracking import report_exception


async def handle_connection_exception(
	ws: WebSocket, exc: Exception
) -> None:
	"""Report failures and close an open transport."""
	if not isinstance(exc, WebSocketConnectionException):
		raise exc
	report_exception(
		exc,
		'websocket_connection_failed',
		{
			'transport': 'websocket',
			'connection_id': exc.connection_id,
			'request_id': exc.request_id,
			'close_code': exc.code,
			'reason': exc.reason,
		},
		user_id=exc.user_id,
		posthog_session_id=exc.posthog_session_id,
		severity='error' if exc.code == 1011 else 'warning',
	)
	manager = None
	registry = None
	if exc.user_id is not None and getattr(
		ws.state, 'registered', False
	):
		try:
			registry = get_websocket_registry()
			manager = await registry.get_connection(
				exc.user_id, exc.connection_id
			)
		except WebSocketRegistryException:
			pass
	if manager is not None and registry is not None:
		await registry.remove_connection(
			manager.user_id,
			manager.connection_id,
			close_code=exc.code,
			reason=exc.reason,
		)
	elif ws.application_state != WebSocketState.DISCONNECTED:
		await ws.close(code=exc.code, reason=exc.reason)
