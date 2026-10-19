"""Receive and validate client WebSocket requests."""

from fastapi import WebSocket, WebSocketException

from api.websocket.helpers.guards import guard_ws_content
from schemas.api.ws.request import WebSocketRequest
from shared.ids import generate_uuid_str


async def receive_ws_request(
	ws: WebSocket, user_id: str
) -> WebSocketRequest:
	"""Parse JSON and reject malformed request envelopes."""
	content = await ws.receive_text()
	await guard_ws_content(user_id, content)
	try:
		request = WebSocketRequest.model_validate_json(content)
	except ValueError as exc:
		raise WebSocketException(
			code=1008,
			reason='Invalid WebSocket request.',
		) from exc
	request.request_id = request.request_id or generate_uuid_str()
	return request
