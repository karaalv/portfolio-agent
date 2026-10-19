"""Deliver agent events to the requesting socket when supplied."""

from fastapi import WebSocketException

from api.websocket import send_connection
from schemas.api.ws.response import WebSocketResponse


async def send_agent_ws_response(
	user_id: str,
	connection_id: str | None,
	response: WebSocketResponse,
) -> None:
	"""Queue an event or skip socket output for direct callers."""
	if connection_id is None:
		return
	if not await send_connection(user_id, connection_id, response):
		raise WebSocketException(
			code=1013,
			reason='Unable to deliver agent response.',
		)
