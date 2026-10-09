"""
This module contains agent routes for
the Agent API.
"""

from fastapi import (
	APIRouter,
	Depends,
	WebSocket,
	WebSocketDisconnect,
)

from agent.main import chat
from api.common.authentication import (
	validate_frontend_token,
	verify_jwt_ws,
)
from api.common.responses import error_response
from api.common.schemas import SocketMessage
from api.common.socket_registry import (
	add_connection_registry,
	delete_connection_registry,
	send_message_ws,
)
from users.retrieval import does_user_exist

# --- Constants ---

agent_router = APIRouter()

# --- Agent Routes ---


@agent_router.websocket(
	'/ws/chat', dependencies=[Depends(verify_jwt_ws)]
)
async def agent_chat_ws(ws: WebSocket):
	"""
	WebSocket endpoint for agent chat.
	"""
	token = ws.query_params.get('ft')
	if not token:
		return error_response(
			'Missing frontend token', status_code=400
		)

	# Validate token - HTTP exception raised
	# on validation
	validate_frontend_token(token)

	user_id = ws.cookies.get('UUID')
	if not user_id:
		return error_response('Missing user_id', status_code=400)

	if not await does_user_exist(user_id):
		return error_response(
			'User does not exist', status_code=404
		)

	# Start socket connection
	await ws.accept()
	await add_connection_registry(user_id=user_id, ws=ws)

	try:
		while True:
			data: dict = await ws.receive_json()
			socket_message = SocketMessage(**data)

			# Ping for connection
			if socket_message.type == 'ping':
				await send_message_ws(
					user_id=user_id,
					type='ping',
					data='pong',
				)
				continue

			# Chat responses
			user_input = socket_message.data

			response = await chat(
				user_id=user_id,
				user_input=str(user_input),
			)

			# Handle streamed responses
			if not response:
				continue

			await send_message_ws(
				user_id=user_id,
				type='agent_memory',
				data=response,
			)
	except WebSocketDisconnect:
		await delete_connection_registry(user_id=user_id)
