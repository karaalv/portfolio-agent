"""
This module contains agent routes for
the Agent API.
"""
from fastapi import APIRouter, Request, Depends
from fastapi import WebSocket, WebSocketDisconnect
from api.common.schemas import SocketMessage
from api.common.utils import api_exception_handler
from api.common.responses import success_response, error_response
from agent.main import chat
from agent.memory.main import retrieve_memory, delete_memory
from api.common.authentication import verify_frontend_token, verify_jwt
from api.common.authentication import validate_frontend_token, verify_jwt_ws
from api.common.socket_registry import add_connection_registry, delete_connection_registry
from api.common.socket_registry import send_message_ws
from users.main import does_user_exist

# --- Constants --- 

router = APIRouter()

# --- Agent Routes ---

@router.websocket(
    "/ws/chat",
    dependencies=[
        Depends(verify_jwt_ws)
    ]
)
async def agent_chat_ws(ws: WebSocket):
    """
    WebSocket endpoint for agent chat.
    """
    token = ws.query_params.get("ft")
    if not token:
        return error_response(
            "Missing frontend token",
            status_code=400
        )
    
    # Validate token - HTTP exception raised
    # on validation
    validate_frontend_token(token)
    
    user_id = ws.cookies.get("UUID")
    if not user_id:
        return error_response(
            "Missing user_id",
            status_code=400
        )

    if not await does_user_exist(user_id):
        return error_response(
            "User does not exist",
            status_code=404
        )

    # Start socket connection
    await ws.accept()
    await add_connection_registry(user_id=user_id, ws=ws)
    
    try:
        while True:
            data: dict = await ws.receive_json()
            socket_message = SocketMessage(**data)

            # Ping for connection
            if socket_message.type == "ping":
                await send_message_ws(
                    user_id=user_id,
                    type="ping",
                    data="pong"
                )
                continue

            user_input = socket_message.data

            response = await chat(
                user_id=user_id,
                input=str(user_input)
            )

            # Handle streamed responses
            if not response:
                continue

            await send_message_ws(
                user_id=user_id,
                type="agent_memory",
                data=response
            )
    except WebSocketDisconnect:
        await delete_connection_registry(user_id=user_id)

# --- HTTP Based Routes ---

@router.get(
    "/memory",
    dependencies=[
        Depends(verify_frontend_token),
        Depends(verify_jwt)
    ]
)
@api_exception_handler("Get user memory")
async def get_memory_api(request: Request):
    """
    Retrieves the memory for a user.
    """
    cookies = request.cookies
    user_id = cookies.get("UUID")

    if not user_id:
        return error_response(
            "Missing user_id",
            status_code=400
        )

    if not await does_user_exist(user_id):
        return error_response(
            "User does not exist",
            status_code=404
        )

    memory = await retrieve_memory(
        user_id,
        to_str=False
    )

    return success_response(
        message="Successfully retrieved user memory",
        data=memory
    )

@router.delete(
    "/clear-memory", 
    dependencies=[
        Depends(verify_frontend_token),
        Depends(verify_jwt)
    ]
)
@api_exception_handler("Delete user memory")
async def delete_memory_api(request: Request):
    """
    Deletes the memory for a user.
    """
    cookies = request.cookies
    user_id = cookies.get("UUID")

    if not user_id:
        return error_response(
            "Missing user_id",
            status_code=400
        )

    if not await does_user_exist(user_id):
        return error_response(
            "User does not exist",
            status_code=404
        )

    result = await delete_memory(
        user_id=user_id
    )

    if result is False:
        return error_response(
            "Failed to delete user memory",
            status_code=500
        )

    return success_response(
        message="Successfully deleted user memory"
    )