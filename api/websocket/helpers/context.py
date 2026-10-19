"""Resolve handshake correlation before authentication checks."""

from fastapi import WebSocket

from exceptions.websocket import WebSocketConnectionException
from shared.ids import generate_uuid_str


def initialise_connection_context(ws: WebSocket) -> None:
	"""Set correlation once without trusting client user identity."""
	if not getattr(ws.state, 'connection_id', None):
		ws.state.connection_id = generate_uuid_str()
		ws.state.request_id = (
			ws.query_params.get('request_id') or generate_uuid_str()
		)
		ws.state.posthog_session_id = (
			ws.query_params.get('session_id', '').strip() or None
		)


def connection_exception(
	ws: WebSocket, code: int, reason: str
) -> WebSocketConnectionException:
	"""Attach the currently resolved context to a socket failure."""
	initialise_connection_context(ws)
	return WebSocketConnectionException(
		connection_id=ws.state.connection_id,
		request_id=ws.state.request_id,
		code=code,
		reason=reason,
		user_id=getattr(ws.state, 'user_id', None),
		posthog_session_id=ws.state.posthog_session_id,
	)
