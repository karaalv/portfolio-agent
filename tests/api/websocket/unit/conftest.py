"""Provide isolated sockets and owned connection lifecycles."""

from collections.abc import AsyncIterator, Callable
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from api.websocket.manager import WebSocketManager
from api.websocket.registry import WebSocketRegistry
from schemas.api.ws.response import WebSocketWarningResponse


@pytest.fixture
def socket() -> AsyncMock:
	"""Expose awaitable transport operations without a server."""
	return _create_socket()


@pytest.fixture
def socket_factory() -> Callable[[], AsyncMock]:
	"""Create independent transports for multiple connections."""
	return _create_socket


@pytest.fixture
def response() -> WebSocketWarningResponse:
	"""
	Create application output with fallback metadata.
	"""
	return create_ws_warning_response('Notice')


@pytest_asyncio.fixture
async def manager(
	socket: AsyncMock,
) -> AsyncIterator[WebSocketManager]:
	"""Close manager tasks even when assertions fail."""
	instance = WebSocketManager('user', 'connection', socket)
	try:
		yield instance
	finally:
		await instance.close()


@pytest_asyncio.fixture
async def registry() -> AsyncIterator[WebSocketRegistry]:
	"""Stop cleanup and all registered managers at teardown."""
	instance = WebSocketRegistry()
	try:
		yield instance
	finally:
		await instance.stop()


def _create_socket() -> AsyncMock:
	"""Represent a socket accepted by the controller."""
	transport = AsyncMock(spec=WebSocket)
	transport.client_state = WebSocketState.CONNECTED
	transport.application_state = WebSocketState.CONNECTED
	return transport
