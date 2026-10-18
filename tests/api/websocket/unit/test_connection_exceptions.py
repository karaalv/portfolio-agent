"""Check correlation on handshake failures before route execution."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, WebSocket
from starlette.websockets import WebSocketState

from api.dependencies.auth import ip
from api.websocket.helpers import exception_capture
from exceptions.websocket import WebSocketConnectionException

pytestmark = pytest.mark.unit


async def test_missing_user_closes_socket_without_registry_lookup(
	monkeypatch,
):
	"""A failed unauthenticated handshake has no manager to remove."""
	ws = AsyncMock(spec=WebSocket)
	ws.application_state = WebSocketState.CONNECTING
	registry_getter = Mock(
		side_effect=AssertionError('registry accessed')
	)
	monkeypatch.setattr(
		exception_capture, 'get_websocket_registry', registry_getter
	)
	monkeypatch.setattr(exception_capture, 'report_exception', Mock())
	exc = WebSocketConnectionException(
		'connection', 'request', 1008, 'Denied'
	)
	await exception_capture.handle_connection_exception(ws, exc)
	registry_getter.assert_not_called()
	ws.close.assert_awaited_once_with(code=1008, reason='Denied')


async def test_registered_failure_removes_using_manager_identity(
	monkeypatch,
):
	"""Use non-null registry-owned identity for connection removal."""
	ws = AsyncMock(spec=WebSocket)
	ws.state = SimpleNamespace(registered=True)
	manager = SimpleNamespace(
		user_id='visitor', connection_id='connection'
	)
	registry = SimpleNamespace(
		get_connection=AsyncMock(return_value=manager),
		remove_connection=AsyncMock(),
	)
	monkeypatch.setattr(
		exception_capture, 'get_websocket_registry', lambda: registry
	)
	monkeypatch.setattr(exception_capture, 'report_exception', Mock())
	exc = WebSocketConnectionException(
		'connection', 'request', 1011, 'Failed', user_id='visitor'
	)
	await exception_capture.handle_connection_exception(ws, exc)
	registry.remove_connection.assert_awaited_once_with(
		'visitor',
		'connection',
		close_code=1011,
		reason='Failed',
	)
	ws.close.assert_not_awaited()


@pytest.mark.parametrize('client', [None, ('127.0.0.1', 1234)])
async def test_ip_denials_have_handshake_context(monkeypatch, client):
	"""Retain correlation without adopting browser user identity."""
	ws = WebSocket(
		{
			'type': 'websocket',
			'path': '/agent/ws/agent-chat',
			'query_string': b'session_id=session&request_id=request',
			'headers': [(b'x-posthog-distinct-id', b'forged')],
			'client': client,
		},
		receive=AsyncMock(),
		send=AsyncMock(),
	)
	monkeypatch.setattr(
		ip,
		'retrieve_application_limiter',
		AsyncMock(side_effect=HTTPException(403, 'Blocked')),
	)
	with pytest.raises(WebSocketConnectionException) as caught:
		await ip.require_ws_ip_access(ws)
	assert caught.value.code == 1008
	assert caught.value.connection_id
	assert caught.value.request_id == 'request'
	assert caught.value.posthog_session_id == 'session'
	assert caught.value.user_id is None
