"""Retrieve request IDs and server-resolved client addresses."""

from fastapi import (
	HTTPException,
	Request,
	WebSocket,
	WebSocketException,
	status,
)


def get_request_id(request: Request) -> str:
	"""
	Extract request ID from the request header
	or request state if not found in headers.
	"""
	header_request_id = request.headers.get('X-Request-ID')
	if header_request_id:
		return header_request_id
	return getattr(request.state, 'request_id', '')


def get_http_ip(request: Request) -> str:
	"""Return the client host or reject a missing HTTP address.

	Trusted proxy headers must be resolved by the server.
	"""
	if request.client is None or not request.client.host.strip():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail='Client IP address is missing.',
		)
	return request.client.host


def get_ws_ip(websocket: WebSocket) -> str:
	"""Return the client host or reject a missing socket address.

	Trusted proxy headers must be resolved by the server.
	"""
	if (
		websocket.client is None
		or not websocket.client.host.strip()
	):
		raise WebSocketException(
			code=status.WS_1008_POLICY_VIOLATION,
			reason='Client IP address is missing.',
		)
	return websocket.client.host
