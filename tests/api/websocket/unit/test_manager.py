"""Check ordered delivery, backpressure and task cleanup."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from api.websocket import manager as module
from api.websocket.helpers.responses import (
	create_ws_warning_response,
)
from api.websocket.manager import WebSocketManager
from exceptions.websocket import WebSocketManagerException
from schemas.api.ws.response import WebSocketWarningResponse

pytestmark = pytest.mark.unit


async def test_queue_captures_current_request_id(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
) -> None:
	"""Keep queued IDs stable without mutating shared output."""
	fallback_id = response.meta.request_id
	manager.record_message('first-request')
	assert await manager.send_message(response)
	manager.record_message('second-request')
	assert await manager.send_message(response)
	first = manager._message_queue.get_nowait()
	second = manager._message_queue.get_nowait()
	assert first.meta.request_id == 'first-request'
	assert second.meta.request_id == 'second-request'
	assert response.meta.request_id == fallback_id
	manager._message_queue.task_done()
	manager._message_queue.task_done()


async def test_delivery_preserves_order(
	manager: WebSocketManager, socket: AsyncMock
) -> None:
	"""
	One sender delivers queued application messages in order.
	"""
	manager.record_message('request')
	manager.start()
	for number in range(3):
		assert await manager.send_message(
			create_ws_warning_response(str(number))
		)
	await asyncio.wait_for(manager._message_queue.join(), 1)
	messages = [
		call.args[0]
		for call in socket.send_json.await_args_list
		if call.args[0]['type'] == 'warning'
	]
	assert [item['payload'] for item in messages] == [
		'0',
		'1',
		'2',
	]
	assert all(
		item['meta']['request_id'] == 'request' for item in messages
	)


async def test_start_and_close_are_idempotent(
	manager: WebSocketManager, socket: AsyncMock
) -> None:
	"""
	Repeated lifecycle calls do not duplicate tasks or close.
	"""
	manager.start()
	sender, heartbeat = (
		manager._sender_task,
		manager._heartbeat_task,
	)
	manager.start()
	assert manager._sender_task is sender
	assert manager._heartbeat_task is heartbeat
	await manager.close()
	await manager.close()
	assert sender is not None and sender.done()
	assert heartbeat is not None and heartbeat.done()
	socket.close.assert_awaited_once_with(
		code=1000, reason='Normal closure'
	)


async def test_closed_manager_rejects_output_and_restart(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
) -> None:
	"""
	A closed manager retains context in its lifecycle error.
	"""
	manager.record_message('request')
	await manager.close()
	assert not await manager.send_message(response)
	with pytest.raises(WebSocketManagerException) as caught:
		manager.start()
	assert caught.value.connection_id == 'connection'
	assert caught.value.user_id == 'user'
	assert caught.value.request_id == 'request'
	assert caught.value.operation == 'start'


async def test_queue_waits_for_space(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
) -> None:
	"""A full queue accepts output when capacity becomes free."""
	manager._message_queue = asyncio.Queue(maxsize=1)
	assert await manager.send_message(response)
	pending = asyncio.create_task(manager.send_message(response))
	await asyncio.sleep(0)
	assert not pending.done()
	manager._message_queue.get_nowait()
	manager._message_queue.task_done()
	assert await asyncio.wait_for(pending, 1)
	assert not manager.is_closed


async def test_full_queue_closes_with_1013(
	manager: WebSocketManager,
	socket: AsyncMock,
	response: WebSocketWarningResponse,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""
	Exhausted capacity closes the socket with code 1013.
	"""
	monkeypatch.setattr(module, '_QUEUE_PUT_TIMEOUT_SECONDS', 0.01)
	manager._message_queue = asyncio.Queue(maxsize=1)
	assert await manager.send_message(response)
	assert not await manager.send_message(response)
	socket.close.assert_awaited_once_with(
		code=1013, reason='Outbound queue exhausted'
	)
	assert manager.is_closed
	await asyncio.wait_for(manager._message_queue.join(), 1)


async def test_close_unblocks_queue_producers(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
) -> None:
	"""Shutdown releases callers waiting for queue capacity."""
	manager._message_queue = asyncio.Queue(maxsize=1)
	await manager.send_message(response)
	pending = asyncio.create_task(manager.send_message(response))
	await asyncio.sleep(0)
	await manager.close()
	assert not await asyncio.wait_for(pending, 1)


async def test_enqueue_cancellation_propagates(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
) -> None:
	"""Cancelling one producer does not close the connection."""
	manager._message_queue = asyncio.Queue(maxsize=1)
	await manager.send_message(response)
	pending = asyncio.create_task(manager.send_message(response))
	await asyncio.sleep(0)
	pending.cancel()
	with pytest.raises(asyncio.CancelledError):
		await pending
	assert not manager.is_closed


async def test_unexpected_enqueue_error_drops_item(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Unexpected enqueue errors drop output without closing."""
	monkeypatch.setattr(
		manager._message_queue,
		'put',
		AsyncMock(side_effect=RuntimeError('Queue failed')),
	)
	assert not await manager.send_message(response)
	assert not manager.is_closed


@pytest.mark.parametrize(
	'failure, code',
	[
		(RuntimeError('Broken transport'), 1011),
		(TimeoutError('Slow transport'), 1013),
	],
)
async def test_sender_failure_closes_without_self_wait(
	manager: WebSocketManager,
	socket: AsyncMock,
	failure: Exception,
	code: int,
) -> None:
	"""A failing sender closes without awaiting its own task."""
	socket.send_json.side_effect = failure
	manager.start()
	await asyncio.wait_for(manager._close_complete.wait(), 1)
	await manager.close()
	assert socket.close.await_args is not None
	assert socket.close.await_args.kwargs['code'] == code
	assert manager._sender_task is not None
	await asyncio.wait_for(manager._sender_task, 1)
	assert manager._heartbeat_task is not None
	assert manager._heartbeat_task.done()


async def test_stalled_send_hits_delivery_timeout(
	manager: WebSocketManager,
	socket: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""
	A transport that never returns cannot retain the sender.
	"""
	monkeypatch.setattr(module, '_SEND_TIMEOUT_SECONDS', 0.01)
	blocked = asyncio.Event()

	async def stall(_: object) -> None:
		await blocked.wait()

	socket.send_json.side_effect = stall
	manager.start()
	await asyncio.wait_for(manager._close_complete.wait(), 1)
	assert socket.close.await_args is not None
	assert socket.close.await_args.kwargs['code'] == 1013


async def test_heartbeat_failure_closes_with_1011(
	manager: WebSocketManager,
	socket: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Unexpected heartbeat errors stop both owned tasks."""

	def fail(**_: object) -> None:
		raise RuntimeError('Heartbeat construction failed')

	monkeypatch.setattr(module, 'create_ws_heartbeat_response', fail)
	manager.start()
	await asyncio.wait_for(manager._close_complete.wait(), 1)
	assert socket.close.await_args is not None
	assert socket.close.await_args.kwargs['code'] == 1011


async def test_activity_ignores_heartbeats(
	manager: WebSocketManager,
	response: WebSocketWarningResponse,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""
	Only application traffic refreshes the inactivity clock.
	"""
	created = manager.created_at
	now = created + timedelta(minutes=2)
	monkeypatch.setattr(module, 'get_utc_datetime_now', lambda: now)
	manager.start()
	await asyncio.sleep(0)
	await asyncio.wait_for(manager._message_queue.join(), 1)
	assert manager.last_message_at == created
	manager.record_message('incoming')
	assert manager.last_message_at == now
	assert manager.request_id == 'incoming'
	now += timedelta(minutes=1)
	await manager.send_message(response)
	await asyncio.wait_for(manager._message_queue.join(), 1)
	assert manager.last_message_at == now
	assert manager.created_at == created


async def test_close_failure_finishes_cleanup(
	manager: WebSocketManager,
	socket: AsyncMock,
) -> None:
	"""A close transport error cannot strand shutdown waiters."""
	socket.close.side_effect = RuntimeError('Already disconnected')
	await asyncio.gather(manager.close(), manager.close())
	assert manager._close_complete.is_set()
