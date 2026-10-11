"""Receive and validate client WebSocket requests."""

from fastapi import WebSocket, WebSocketException

from schemas.api.ws.request import WebSocketRequest
from shared.ids import generate_uuid_str


async def receive_ws_request(ws: WebSocket) -> WebSocketRequest:
	"""Parse JSON and reject malformed request envelopes."""
	try:
		request = WebSocketRequest.model_validate(
			await ws.receive_json()
		)
	except ValueError as exc:
		raise WebSocketException(
			code=1008,
			reason='Invalid WebSocket request.',
		) from exc
	request.request_id = (
		request.request_id or generate_uuid_str()
	)
	return request
