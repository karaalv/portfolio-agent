"""
This module contains the socket registry
used in the server for managing WebSocket
connections.
"""
from typing import Any
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

async def delete_connection_registry(
    user_id: str
):
    """
    Delete a WebSocket connection 
    from the registry.
    """
    if user_id in _active_connections.keys():
        del _active_connections[user_id]

def get_connection_registry(
    user_id: str
) -> SocketManager | None:
    """
    Retrieve a WebSocket connection 
    from the registry.
    """
    if user_id in _active_connections.keys():
        return _active_connections[user_id]
    else:
        return None

# --- Communication ---

async def send_message_ws(
    user_id: str,
    type: str,
    data: Any,
    success: bool = True,
    message: str = "Data sent successfully"
):
    connection = get_connection_registry(user_id)
    if connection:
        await connection.send_message(
            type=type,
            data=data,
            success=success,
            message=message
        )
