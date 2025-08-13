"""
This module contains the socket registry
used in the server for managing WebSocket
connections.
"""
from typing import Any, Optional
from fastapi import WebSocket
from api.common.socket_manager import SocketManager

_active_connections: dict[str, SocketManager] = {}

# --- Connection Management ---

async def add_connection_registry(
    user_id: str, 
    ws: WebSocket
):
    """
    Create a new WebSocket connection and 
    add it to the registry.
    """
    manager = SocketManager(user_id=user_id, ws=ws)
    _active_connections[user_id] = manager
    return manager

async def delete_connection_registry(
    user_id: str
):
    """
    Delete a WebSocket connection 
    from the registry.
    """
    if user_id in _active_connections:
        del _active_connections[user_id]

async def get_connection_registry(
    user_id: str
) -> SocketManager | None:
    """
    Retrieve a WebSocket connection 
    from the registry.
    """
    if user_id not in _active_connections.keys():
        raise ValueError(
            f"No active connection for user_id: "
            f"{user_id}"
        )

    return _active_connections.get(user_id, None)

# --- Communication ---

async def send_message_ws(
    user_id: str,
    type: str,
    data: Any,
    success: bool = True,
    message: str = "Data sent successfully"
):
    connection = await get_connection_registry(user_id)
    if connection:
        await connection.send_message(
            type=type,
            data=data,
            success=success,
            message=message
        )
