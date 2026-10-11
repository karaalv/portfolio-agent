"""Check tracking isolation, removal and inactivity cleanup."""

import asyncio
from collections.abc import Callable
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from api.websocket import registry as module
from api.websocket.registry import WebSocketRegistry
from exceptions.websocket import WebSocketRegistryException
from schemas.api.ws.response import WebSocketWarningResponse
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


async def test_tracking_is_scoped_by_user_and_connection(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
) -> None:
	"""
	Identical connection IDs for different users stay separate.
	"""
	first = await registry.add_connection(
		'a', 'one', socket_factory()
	)
	second = await registry.add_connection(
		'b', 'one', socket_factory()
	)
	await registry.add_connection('a', 'two', socket_factory())
	assert await registry.has_user('a')
	assert await registry.has_connection('a', 'one')
	assert await registry.count_connections('a') == 2
	assert await registry.get_connection('a', 'one') is first
	assert await registry.get_connection('b', 'one') is second
	assert not await registry.has_user('missing')
	assert not await registry.has_connection('a', 'missing')
	assert await registry.count_connections('missing') == 0


async def test_concurrent_duplicates_keep_one_manager(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
) -> None:
	"""
	Concurrent registrations cannot replace or leak a manager.
	"""
	sockets = [socket_factory() for _ in range(5)]
	results = await asyncio.gather(
		*(
			registry.add_connection('user', 'connection', socket)
			for socket in sockets
		),
		return_exceptions=True,
	)
	assert (
		sum(
			isinstance(item, WebSocketRegistryException)
			for item in results
		)
		== 4
	)
	assert await registry.count_connections('user') == 1
	tracked = await registry.get_connection('user', 'connection')
	assert tracked is not None
	await registry.close_all_connections()
	assert tracked.is_closed
	assert sum(s.close.await_count for s in sockets) == 1


async def test_send_targets_only_one_connection(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
	response: WebSocketWarningResponse,
) -> None:
	"""Sending does not broadcast to other sockets or users."""
	first, other = socket_factory(), socket_factory()
	manager = await registry.add_connection('a', 'one', first)
	await registry.add_connection('a', 'two', other)
	assert await registry.send_connection('a', 'one', response)
	await asyncio.wait_for(manager._message_queue.join(), 1)
	assert any(
		call.args[0]['type'] == 'warning'
		for call in first.send_json.await_args_list
	)
	assert not any(
		call.args[0]['type'] == 'warning'
		for call in other.send_json.await_args_list
	)
	assert not await registry.send_connection(
		'b', 'one', response
	)


@pytest.mark.parametrize(
	'operation',
	[
		'connection',
		'user',
		'users',
		'all',
	],
)
async def test_removal_closes_and_clears_selected_scope(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
	operation: str,
) -> None:
	"""Removal closes selected managers and preserves others."""
	sockets = [socket_factory() for _ in range(3)]
	for user, connection, socket in zip(
		['a', 'a', 'b'],
		['one', 'two', 'one'],
		sockets,
		strict=True,
	):
		await registry.add_connection(user, connection, socket)
	if operation == 'connection':
		await registry.remove_connection('a', 'one')
		await registry.remove_connection('a', 'one')
		expected = [True, False, False]
	elif operation == 'user':
		await registry.remove_user_connections('a')
		expected = [True, True, False]
	elif operation == 'users':
		await registry.remove_users_connections(
			['a', 'a', 'missing']
		)
		expected = [True, True, False]
	else:
		await registry.close_all_connections()
		expected = [True, True, True]
	assert [
		bool(s.close.await_count) for s in sockets
	] == expected
	assert await registry.count_connections('a') == (
		1 if operation == 'connection' else 0
	)
	assert await registry.has_user('b') is (operation != 'all')


async def test_prune_handles_idle_boundary_and_closed_sockets(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""
	Expire exactly-hour-old activity but retain fresh sockets.
	"""
	now = get_utc_datetime_now()
	monkeypatch.setattr(
		module, 'get_utc_datetime_now', lambda: now
	)
	idle = await registry.add_connection(
		'a', 'idle', socket_factory()
	)
	fresh = await registry.add_connection(
		'a', 'fresh', socket_factory()
	)
	closed = await registry.add_connection(
		'b', 'closed', socket_factory()
	)
	idle.last_message_at = now - timedelta(hours=1)
	fresh.last_message_at = now - timedelta(minutes=59)
	await closed.close()
	await registry._prune_inactive_connections()
	assert idle.is_closed
	assert not fresh.is_closed
	assert await registry.count_connections('a') == 1
	assert not await registry.has_user('b')
	assert await registry.get_connection('a', 'fresh') is fresh


async def test_background_pruning_runs_and_stops(
	registry: WebSocketRegistry,
	socket: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""
	The actual cleanup task prunes without a manual invocation.
	"""
	monkeypatch.setattr(module, '_PRUNE_INTERVAL_SECONDS', 0.01)
	manager = await registry.add_connection('a', 'idle', socket)
	manager.last_message_at -= timedelta(hours=2)
	registry.start()
	task = registry._pruner_task
	registry.start()
	assert registry._pruner_task is task
	await asyncio.wait_for(manager._close_complete.wait(), 1)
	assert not await registry.has_user('a')
	await registry.stop()
	assert task is not None and task.done()
	with pytest.raises(WebSocketRegistryException):
		registry.start()
	with pytest.raises(WebSocketRegistryException):
		await registry.add_connection('a', 'new', socket)


async def test_slow_close_does_not_hold_registry_lock(
	registry: WebSocketRegistry,
	socket_factory: Callable[[], AsyncMock],
) -> None:
	"""
	Other users remain accessible during slow socket closure.
	"""
	entered, release = asyncio.Event(), asyncio.Event()

	async def slow_close(**_: object) -> None:
		entered.set()
		await release.wait()

	slow = socket_factory()
	slow.close.side_effect = slow_close
	await registry.add_connection('a', 'slow', slow)
	other = await registry.add_connection(
		'b', 'live', socket_factory()
	)
	removal = asyncio.create_task(
		registry.remove_connection('a', 'slow')
	)
	try:
		await asyncio.wait_for(entered.wait(), 1)
		assert (
			await asyncio.wait_for(
				registry.get_connection('b', 'live'), 1
			)
			is other
		)
	finally:
		release.set()
		await asyncio.wait_for(removal, 1)


async def test_cancelled_removal_finishes_detached_cleanup(
	registry: WebSocketRegistry,
	socket: AsyncMock,
) -> None:
	"""
	Cancellation cannot abandon detached connection managers.
	"""
	entered, release = asyncio.Event(), asyncio.Event()

	async def slow_close(**_: object) -> None:
		entered.set()
		await release.wait()

	socket.close.side_effect = slow_close
	manager = await registry.add_connection('a', 'one', socket)
	removal = asyncio.create_task(
		registry.remove_user_connections('a')
	)
	try:
		await asyncio.wait_for(entered.wait(), 1)
		removal.cancel()
		await asyncio.sleep(0)
		assert not removal.done()
	finally:
		release.set()
	with pytest.raises(asyncio.CancelledError):
		await asyncio.wait_for(removal, 1)
	assert manager._close_complete.is_set()
	assert not await registry.has_user('a')
