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
from api.websocket.helpers.context import (
	connection_exception,
	initialise_connection_context,
)
from api.websocket.helpers.guards import guard_agent_input
from api.websocket.helpers.ratelimit import (
	agent_message_rate_limit,
)
from api.websocket.helpers.requests import receive_ws_request
from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from exceptions.websocket import WebSocketConnectionException
from schemas.api.ws.request import WebSocketRequestType

agent_router = APIRouter()


@agent_router.websocket('/ws/agent-chat')
async def agent_chat_ws(
	ws: WebSocket,
	ip_address: WSIPAccess,
	access_token: str | None = None,
	request_id: str | None = None,
	session_id: str | None = None,
) -> None:
	"""Resolve an identity and run sequential agent turns.

	The optional access_token comes from the query string.
	Use the query request_id for handshake response metadata.
	Retain the query session_id as browser replay context only.
	Issue a claim token after registering anonymous sockets.
	"""
	initialise_connection_context(ws)
	connection_id = ws.state.connection_id
	request_id = ws.state.request_id
	posthog_session_id = ws.state.posthog_session_id
	registry = None
	user_id = None
	failed = False
	try:
		user_id, claim_token = await resolve_ws_user(
			access_token, websocket=ws
		)
		ws.state.user_id = user_id
		registry = get_websocket_registry()
		await ws.accept()
		manager = await registry.add_connection(
			user_id,
			connection_id,
			ws,
			request_id,
			posthog_session_id=posthog_session_id,
		)
		ws.state.registered = True
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
			async with agent_message_rate_limit(user_id, ip_address):
				await agent_chat(
					user_id=user_id,
					user_input=user_input,
					connection_id=connection_id,
					posthog_session_id=posthog_session_id,
				)
	except WebSocketDisconnect:
		pass
	except WebSocketConnectionException:
		failed = True
		raise
	except WebSocketException as exc:
		failed = True
		raise connection_exception(
			ws, exc.code, exc.reason or ''
		) from exc
	except Exception as exc:
		failed = True
		raise connection_exception(
			ws, 1011, 'Unable to process chat.'
		) from exc
	finally:
		if (
			not failed
			and registry is not None
			and user_id is not None
		):
			await registry.remove_connection(user_id, connection_id)
