"""Exercise manager and registry over real ASGI WebSockets."""

from datetime import timedelta

import pytest
from starlette.websockets import WebSocketDisconnect

from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from api.websocket.registry import WebSocketRegistry
from tests.api.websocket.integration.websocket_harness import (
	WebSocketHarness,
)

pytestmark = pytest.mark.integration


def test_heartbeat_and_ordered_agent_envelopes(
	harness: WebSocketHarness,
) -> None:
	"""
	A client receives heartbeat and structured output in order.
	"""
	with harness.client.websocket_connect('/ws/user/one') as ws:
		heartbeat = ws.receive_json()
		assert heartbeat['type'] == 'heartbeat'
		assert heartbeat['payload'] == 'ping'
		ws.send_json({'type': 'heartbeat', 'payload': 'pong'})
		ws.send_json({'type': 'agent_message', 'payload': 'Hello'})
		messages = [ws.receive_json() for _ in range(3)]
		assert [message['type'] for message in messages] == [
			'agent_start',
			'agent_delta',
			'agent_end',
		]
		assert messages[1]['payload']['payload'] == 'Hello'
		assert messages[1]['payload']['user_id'] == 'user'
		assert all(
			message['meta']['request_id'] == 'echo-request'
			for message in messages
		)
	assert not harness.call(harness.registry.has_user, 'user')


def test_targeted_delivery_isolates_connections_and_users(
	harness: WebSocketHarness,
) -> None:
	"""A targeted warning cannot appear on another connection."""
	with (
		harness.client.websocket_connect('/ws/a/one') as first,
		harness.client.websocket_connect('/ws/a/two') as second,
		harness.client.websocket_connect('/ws/b/one') as other,
	):
		for socket in (first, second, other):
			assert socket.receive_json()['type'] == 'heartbeat'
		assert (
			harness.call(harness.registry.count_connections, 'a') == 2
		)
		assert harness.call(
			harness.registry.send_connection,
			'a',
			'one',
			create_ws_warning_response('Only first'),
		)
		assert first.receive_json()['payload'] == 'Only first'
		for socket in (second, other):
			socket.send_json(
				{
					'type': 'agent_message',
					'payload': 'Check',
				}
			)
			assert [
				socket.receive_json()['type'] for _ in range(3)
			] == ['agent_start', 'agent_delta', 'agent_end']
	assert not harness.call(harness.registry.has_user, 'a')
	assert not harness.call(harness.registry.has_user, 'b')


@pytest.mark.parametrize('operation', ['remove', 'idle', 'stop'])
def test_server_closure_reaches_client(
	harness: WebSocketHarness,
	operation: str,
) -> None:
	"""
	Removal, inactivity and shutdown send their close codes.
	"""
	with harness.client.websocket_connect('/ws/user/one') as ws:
		ws.receive_json()
		if operation == 'remove':
			harness.call(
				harness.registry.remove_connection,
				'user',
				'one',
				'Connection removed',
				1000,
			)
			expected = 1000
		elif operation == 'idle':
			harness.call(_expire_connection, harness.registry)
			expected = 1001
		else:
			harness.call(harness.registry.stop)
			expected = 1001
		with pytest.raises(WebSocketDisconnect) as caught:
			ws.receive_json()
		assert caught.value.code == expected
	assert not harness.call(harness.registry.has_user, 'user')


async def _expire_connection(
	registry: WebSocketRegistry,
) -> None:
	"""
	Age and prune connection state on the serving event loop.
	"""
	manager = await registry.get_connection('user', 'one')
	assert manager is not None
	manager.last_message_at -= timedelta(hours=2)
	await registry._prune_inactive_connections()
