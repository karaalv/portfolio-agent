"""Own the WebSocket registry within the app process."""

from api.websocket.registry import WebSocketRegistry
from exceptions.websocket import WebSocketRegistryException
from schemas.api.ws.response import WebSocketResponse
from shared.logging import LogStyle, rich_print

_websocket_registry: WebSocketRegistry | None = None

# --- Lifecycle management for the WebSocket registry ---


async def start_websocket_registry() -> None:
	"""Create and start the registry once on the serving loop."""
	if _websocket_registry is not None:
		return
	registry = WebSocketRegistry()
	registry.start()
	set_websocket_registry(registry)
	rich_print(
		'WebSocket registry started.',
		style=LogStyle.SUCCESS,
		prefix='api.websocket.lifecycle',
	)


async def stop_websocket_registry() -> None:
	"""Close connections and stop cleanup before clearing state."""
	if _websocket_registry is None:
		return
	await _websocket_registry.stop()
	set_websocket_registry(None)
	rich_print(
		'WebSocket registry stopped.',
		style=LogStyle.SUCCESS,
		prefix='api.websocket.lifecycle',
	)


def get_websocket_registry() -> WebSocketRegistry:
	"""Return the started registry or raise a lifecycle error."""
	if _websocket_registry is None:
		raise WebSocketRegistryException(
			'The WebSocket registry is not started.',
			'get_websocket_registry',
		)
	return _websocket_registry


def set_websocket_registry(
	registry: WebSocketRegistry | None,
) -> None:
	"""Replace the reference without stopping the old registry."""
	global _websocket_registry
	_websocket_registry = registry


# --- Main API for sending messages through the registry ---


async def send_connection(
	user_id: str,
	connection_id: str,
	message: WebSocketResponse,
) -> bool:
	"""Queue output on one connection in the started registry.

	Return queue acceptance, not client delivery confirmation.
	"""
	return await get_websocket_registry().send_connection(
		user_id, connection_id, message
	)
