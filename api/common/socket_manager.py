"""
This module contains the definition for
the socket manager class which manages
communication and state for a websocket
connection.
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any
from api.common.schemas import SocketResponse, MetaData

class SocketManager:
    """
    Manages WebSocket connections 
    for user.
    """
    def __init__(
        self,
        user_id: str, 
        ws: WebSocket
    ):
        self.user_id = user_id
        self.ws = ws

    # --- Communication ---

    async def send_message(
        self,
        type: str,
        data: Any, 
        success: bool, 
        message: str
    ):
        response = SocketResponse(
            metadata=MetaData(
                success=success,
                message=message
            ),
            type=type,
            data=data
        )

        try:
            await self.ws.send_json(response.model_dump())
        except WebSocketDisconnect:
            await self.close_on_code(
                code=1006,
                reason="Unexpected closure"
            )
        except Exception as e:
            await self.close_on_code(
                code=1006,
                reason=str(e)
            )

    # --- Socket Connection ---

    async def close(self):
        await self.ws.close()

    async def close_on_code(
        self,
        code: int,
        reason: str,
    ):
        await self.ws.close(
            code=code,
            reason=reason
        )

    async def close_on_error(self):
        await self.ws.close(
            code=1006, 
            reason="Error occurred"
        )