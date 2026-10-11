"""Accept portfolio chat sockets and process client messages."""

from fastapi import (
	APIRouter,
	WebSocket,
	WebSocketDisconnect,
	WebSocketException,
)

from agent.input.sanitisation import sanitise_input
from agent.main import agent_chat
from api.dependencies.auth.ip import WSIPAccess
from api.websocket import get_websocket_registry
from api.websocket.helpers.access import (
	resolve_ws_user,
	send_claim_token,
)
from api.websocket.helpers.guards import guard_agent_input
from api.websocket.helpers.ratelimit import (
	agent_message_rate_limit,
)
from api.websocket.helpers.requests import receive_ws_request
from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from schemas.api.ws.request import WebSocketRequestType
from shared.ids import generate_uuid_str

agent_router = APIRouter()


@agent_router.websocket('/ws/agent-chat')
async def agent_chat_ws(
	ws: WebSocket,
	ip_address: WSIPAccess,
	access_token: str | None = None,
	request_id: str | None = None,
) -> None:
	"""Resolve an identity and run sequential agent turns.

	The optional access_token comes from the query string.
	Use the query request_id for handshake response metadata.
	Issue a claim token after registering anonymous sockets.
	"""
	user_id, claim_token = await resolve_ws_user(access_token)
	connection_id = generate_uuid_str()
	request_id = request_id or generate_uuid_str()
	registry = get_websocket_registry()
	await ws.accept()
	try:
		manager = await registry.add_connection(
			user_id, connection_id, ws, request_id
		)
		await send_claim_token(manager, claim_token)
		while True:
			request = await receive_ws_request(ws, user_id)

			# Process incoming WebSocket requests
			if request.type == WebSocketRequestType.HEARTBEAT:
				continue

			# WebSocketRequestType == AGENT_MESSAGE
			manager.record_message(request.request_id)
			await guard_agent_input(user_id, request.payload)
			user_input = sanitise_input(request.payload)
			if not user_input:
				await manager.send_message(
					create_ws_warning_response(
						'Please send a readable text message.'
					)
				)
				continue
			async with agent_message_rate_limit(
				user_id, ip_address
			):
				await agent_chat(
					user_id=user_id,
					user_input=user_input,
					connection_id=connection_id,
				)
	except WebSocketDisconnect:
		pass
	except WebSocketException as exc:
		await registry.remove_connection(
			user_id,
			connection_id,
			reason=exc.reason or '',
			close_code=exc.code,
		)
		return
	except Exception:
		await registry.remove_connection(
			user_id,
			connection_id,
			reason='Unable to process chat.',
			close_code=1011,
		)
		raise
	finally:
		await registry.remove_connection(user_id, connection_id)
