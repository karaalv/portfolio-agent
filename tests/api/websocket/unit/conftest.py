"""Provide isolated sockets and owned connection lifecycles."""

from collections.abc import AsyncIterator, Callable
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import WebSocket

from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from api.websocket.manager import WebSocketManager
from api.websocket.registry import WebSocketRegistry
from schemas.api.ws.response import WebSocketWarningResponse


@pytest.fixture
def socket() -> AsyncMock:
	"""Expose awaitable transport operations without a server."""
	return AsyncMock(spec=WebSocket)


@pytest.fixture
def socket_factory() -> Callable[[], AsyncMock]:
	"""Create independent transports for multiple connections."""
	return lambda: AsyncMock(spec=WebSocket)


@pytest.fixture
def response() -> WebSocketWarningResponse:
	"""
	Create application output with a stable request identity.
	"""
	return create_ws_warning_response('request', 'Notice')


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
