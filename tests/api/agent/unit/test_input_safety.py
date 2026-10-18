"""Exercise cleaning and hard input guards over ASGI sockets."""

from typing import cast
from unittest.mock import ANY, AsyncMock

import pytest
from starlette.testclient import TestClient, WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from api.routes import agent
from api.websocket.helpers import guards
from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from authorisation.jwt.create import create_token
from schemas.security.monitoring.blocked import BlockedEntity
from security.monitoring.blocked import enforcement

_PATH = '/agent/ws/agent-chat'


def _receive_type(ws: WebSocketTestSession, kind: str) -> dict:
	"""Skip periodic heartbeats when awaiting specific output."""
	while True:
		response = ws.receive_json()
		if response['type'] == kind:
			return response


def _assert_closed(ws: WebSocketTestSession, code: int) -> None:
	"""Read pending output until the close frame arrives."""
	with pytest.raises(WebSocketDisconnect) as exc:
		while True:
			ws.receive_json()
	assert exc.value.code == code


@pytest.mark.parametrize('kind', ['agent_message', 'heartbeat'])
def test_oversized_envelope_closes_all_user_connections(
	ws_client: TestClient,
	kind: str,
) -> None:
	"""Block a visitor without closing another visitor's socket."""
	token = create_token('visitor')
	other_token = create_token('other')
	with (
		ws_client.websocket_connect(
			f'{_PATH}?access_token={token}'
		) as first,
		ws_client.websocket_connect(
			f'{_PATH}?access_token={token}'
		) as second,
		ws_client.websocket_connect(
			f'{_PATH}?access_token={other_token}'
		) as other,
	):
		first.send_json({'type': kind, 'payload': 'a' * 16385})
		_assert_closed(first, 1009)
		_assert_closed(second, 1009)
		assert ws_client.portal is not None
		registry = agent.get_websocket_registry()
		assert ws_client.portal.call(registry.has_user, 'other')
		assert not ws_client.portal.call(registry.has_user, 'visitor')
		other.send_json({'type': 'heartbeat', 'payload': 'pong'})
	cast(
		AsyncMock, enforcement.create_block
	).assert_awaited_once_with(
		BlockedEntity.USER,
		'visitor',
		'WebSocket content size limit exceeded.',
	)
	cast(AsyncMock, agent.agent_chat).assert_not_awaited()


def test_oversized_invalid_json_is_blocked_before_parsing(
	ws_client: TestClient,
) -> None:
	"""Malformed giant envelopes still trigger the hard guard."""
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}'
	) as ws:
		ws.send_text('!' * 16385)
		_assert_closed(ws, 1009)
	cast(AsyncMock, enforcement.create_block).assert_awaited_once()


def test_token_guard_runs_before_truncation(
	ws_client: TestClient,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A short test token cap catches the original long payload."""
	monkeypatch.setattr(guards, 'MAX_INPUT_TOKENS', 10)
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}'
	) as ws:
		ws.send_json(
			{
				'type': 'agent_message',
				'payload': 'hello ' * 400,
			}
		)
		_assert_closed(ws, 1009)
	cast(
		AsyncMock, enforcement.create_block
	).assert_awaited_once_with(
		BlockedEntity.USER,
		'visitor',
		'Agent input token limit exceeded.',
	)
	cast(AsyncMock, agent.agent_chat).assert_not_awaited()


def test_noisy_input_warns_then_valid_input_is_cleaned(
	ws_client: TestClient,
) -> None:
	"""Keep the socket usable after empty sanitised input."""

	async def reply(
		user_id: str,
		user_input: str,
		connection_id: str,
		posthog_session_id: str | None = None,
		ai_session_id: str | None = None,
	) -> None:
		"""Expose the text passed to the mocked agent."""
		registry = agent.get_websocket_registry()
		manager = next(iter(registry._registry[user_id].values()))
		await registry.send_connection(
			user_id,
			manager.connection_id,
			create_ws_warning_response(user_input),
		)

	mock = cast(AsyncMock, agent.agent_chat)
	mock.side_effect = reply
	token = create_token('visitor')
	with ws_client.websocket_connect(
		f'{_PATH}?access_token={token}'
	) as ws:
		ws.send_json(
			{
				'type': 'agent_message',
				'payload': 'x' * 50,
				'request_id': 'noise',
			}
		)
		warning = _receive_type(ws, 'warning')
		assert warning['meta']['request_id'] == 'noise'
		mock.assert_not_awaited()
		ws.send_json(
			{
				'type': 'agent_message',
				'payload': '  Hello\x00   Alvin  ',
			}
		)
		assert (
			_receive_type(ws, 'warning')['payload'] == 'Hello Alvin'
		)
	mock.assert_awaited_once_with(
		user_id='visitor',
		user_input='Hello Alvin',
		connection_id=ANY,
		posthog_session_id=None,
		ai_session_id=ANY,
	)
	cast(AsyncMock, enforcement.create_block).assert_not_awaited()
