"""Check socket identity, request handling and close codes."""

from typing import cast
from unittest.mock import ANY, AsyncMock, Mock
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.routes import agent
from api.websocket.helpers import access
from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from authorisation.jwt.create import create_token
from authorisation.jwt.validate import validate_token
from posthog_client import error_tracking
from schemas.security.monitoring.usage import UsageEntity
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.lifecycle import get_limiter

_PATH = '/agent/ws/agent-chat'


def test_handshake_access_failure_retains_verified_user(
	ws_client: TestClient,
	monkeypatch,
) -> None:
	"""Keep validated identity when a later access check fails."""
	capture = Mock()
	monkeypatch.setattr(error_tracking, 'capture_exception', capture)
	cast(
		AsyncMock, access.require_application_access
	).side_effect = HTTPException(403, 'Blocked')
	token = create_token('visitor')
	with pytest.raises(WebSocketDisconnect):
		with ws_client.websocket_connect(
			f'{_PATH}?access_token={token}&session_id=session'
		):
			pass
	capture.assert_called_once()
	assert capture.call_args.args[1] == 'visitor'
	assert capture.call_args.args[2]['sessionId'] == 'session'


def test_failed_handshake_captures_session_before_identity(
	ws_client: TestClient,
	monkeypatch,
) -> None:
	"""Do not invent a user identity for an invalid access token."""
	capture = Mock()
	monkeypatch.setattr(error_tracking, 'capture_exception', capture)
	with pytest.raises(WebSocketDisconnect) as failure:
		with ws_client.websocket_connect(
			f'{_PATH}?access_token=invalid&request_id=handshake&session_id=session-1'
		):
			pass
	assert failure.value.code == 1008
	capture.assert_called_once()
	assert capture.call_args.args[1] is None
	properties = capture.call_args.args[2]
	assert properties['request_id'] == 'handshake'
	assert properties['sessionId'] == 'session-1'
	assert properties['connection_id']


def test_chat_exception_is_captured_once_and_registry_is_cleaned(
	ws_client: TestClient,
	monkeypatch,
) -> None:
	"""Report internal failures once and clean up their connection."""
	capture = Mock()
	monkeypatch.setattr(error_tracking, 'capture_exception', capture)
	cast(AsyncMock, agent.agent_chat).side_effect = RuntimeError(
		'failed'
	)
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}&session_id=session-1'
	) as ws:
		ws.send_json({'type': 'agent_message', 'payload': 'Hello'})
		with pytest.raises(WebSocketDisconnect) as failure:
			while True:
				ws.receive_json()
	assert failure.value.code == 1011
	capture.assert_called_once()
	assert capture.call_args.args[1] == 'visitor'
	assert capture.call_args.args[2]['sessionId'] == 'session-1'
	assert ws_client.portal is not None
	assert not ws_client.portal.call(
		agent.get_websocket_registry().has_user, 'visitor'
	)


@pytest.mark.parametrize(
	'session_id', [None, '', '   ', ' session-1 ']
)
def test_handshake_retains_session_without_changing_identity(
	ws_client: TestClient,
	session_id: str | None,
) -> None:
	"""Keep replay context on the connection and socket state."""
	observed: list[tuple[str, str | None, str | None]] = []

	async def reply(
		user_id, user_input, connection_id, posthog_session_id=None
	):
		registry = agent.get_websocket_registry()
		manager = await registry.get_connection(
			user_id, connection_id
		)
		assert manager is not None
		observed.append(
			(
				manager.user_id,
				manager.posthog_session_id,
				manager.websocket.state.posthog_session_id,
			)
		)
		await manager.send_message(
			create_ws_warning_response('received')
		)

	cast(AsyncMock, agent.agent_chat).side_effect = reply
	query = {
		'access_token': create_token('visitor'),
		'user_id': 'forged',
	}
	if session_id is not None:
		query['session_id'] = session_id
	with ws_client.websocket_connect(
		f'{_PATH}?{urlencode(query)}',
		headers={'X-POSTHOG-DISTINCT-ID': 'forged'},
	) as ws:
		for _ in range(2):
			ws.send_json(
				{'type': 'agent_message', 'payload': 'Hello'}
			)
			while ws.receive_json()['type'] != 'warning':
				pass
	expected = (session_id or '').strip() or None
	assert observed == [('visitor', expected, expected)] * 2


def test_anonymous_socket_issues_token_and_runs_agent(
	ws_client: TestClient,
) -> None:
	"""Create identity once and ignore heartbeat requests."""
	with ws_client.websocket_connect(
		f'{_PATH}?request_id=handshake-request'
	) as ws:
		while True:
			response = ws.receive_json()
			if response['type'] == 'set_user_token':
				break
		assert response['meta']['request_id'] == 'handshake-request'
		assert validate_token(response['payload'])['sub'] == 'visitor'
		ws.send_json({'type': 'heartbeat', 'payload': 'pong'})
		ws.send_json({'type': 'agent_message', 'payload': 'Hello'})
		ws.send_text('invalid json')
		with pytest.raises(WebSocketDisconnect) as exc:
			while True:
				ws.receive_json()
		assert exc.value.code == 1008
	cast(AsyncMock, access.create_user).assert_awaited_once()
	cast(
		AsyncMock, access.create_usage_statistics
	).assert_awaited_once_with(UsageEntity.USER, 'visitor')
	cast(AsyncMock, agent.agent_chat).assert_awaited_once_with(
		user_id='visitor',
		user_input='Hello',
		connection_id=ANY,
		posthog_session_id=None,
	)
	assert ws_client.portal is not None
	assert not ws_client.portal.call(
		agent.get_websocket_registry().has_user,
		'visitor',
	)


@pytest.mark.parametrize(
	'fields',
	[{'request_id': 'client-request'}, {'request_id': None}, {}],
)
def test_message_responses_use_current_request_id(
	ws_client: TestClient,
	fields: dict[str, str | None],
) -> None:
	"""Stamp replies with supplied or generated message IDs."""

	async def reply(
		user_id: str,
		user_input: str,
		connection_id: str,
		posthog_session_id: str | None = None,
	) -> None:
		"""Queue mock output through the actual socket manager."""
		registry = agent.get_websocket_registry()
		manager = next(iter(registry._registry[user_id].values()))
		await registry.send_connection(
			user_id,
			manager.connection_id,
			create_ws_warning_response(user_input),
		)

	cast(AsyncMock, agent.agent_chat).side_effect = reply
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}&request_id=handshake'
	) as ws:
		first_id: str | None = None
		for text in ('First', 'Second'):
			ws.send_json(
				{
					'type': 'agent_message',
					'payload': text,
					**fields,
				}
			)
			while True:
				response = ws.receive_json()
				if response['type'] == 'warning':
					break
			assert response['payload'] == text
			current_id = response['meta']['request_id']
			if fields.get('request_id') is not None:
				assert current_id == fields['request_id']
			else:
				assert current_id and current_id != 'handshake'
				if text == 'Second':
					assert current_id != first_id
			first_id = current_id


def test_existing_token_uses_application_access(
	ws_client: TestClient,
) -> None:
	"""Reuse the signed identity without creating records."""
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}'
	) as ws:
		ws.send_text('{}')
		with pytest.raises(WebSocketDisconnect):
			while True:
				ws.receive_json()
	cast(
		AsyncMock, access.require_application_access
	).assert_awaited_once_with('visitor')
	cast(AsyncMock, access.create_user).assert_not_awaited()
	cast(AsyncMock, agent.agent_chat).assert_not_awaited()


def test_invalid_token_rejects_handshake(
	ws_client: TestClient,
) -> None:
	"""Reject supplied bad tokens instead of creating a user."""
	with pytest.raises(WebSocketDisconnect) as exc:
		with ws_client.websocket_connect(
			f'{_PATH}?access_token=invalid'
		):
			pass
	assert exc.value.code == 1008
	cast(AsyncMock, access.create_user).assert_not_awaited()


def test_application_limit_rejects_handshake(
	ws_client: TestClient,
) -> None:
	"""Translate application throttling into close code 1013."""
	cast(
		AsyncMock, access.require_application_access
	).side_effect = HTTPException(
		status_code=429, detail='Rate limit exceeded.'
	)
	token = create_token('visitor')
	with pytest.raises(WebSocketDisconnect) as exc:
		with ws_client.websocket_connect(
			f'{_PATH}?access_token={token}'
		):
			pass
	assert exc.value.code == 1013


def test_message_limit_closes_socket_before_agent(
	ws_client: TestClient,
) -> None:
	"""Exhaust user capacity and reject the next agent turn."""
	assert ws_client.portal is not None
	limiter = ws_client.portal.call(
		get_limiter,
		ResourceScope.AGENT_MESSAGE,
		ResourceAccessor.USER,
		'visitor',
	)
	ws_client.portal.call(limiter.acquire, limiter.max_rate)
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}'
	) as ws:
		ws.send_json({'type': 'agent_message', 'payload': 'Hello'})
		with pytest.raises(WebSocketDisconnect) as exc:
			while True:
				ws.receive_json()
		assert exc.value.code == 1013
	cast(AsyncMock, agent.agent_chat).assert_not_awaited()
