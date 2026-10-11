"""Queue and deliver messages for one accepted WebSocket."""

import asyncio
import logging

from fastapi import WebSocket

from api.websocket.helpers.responses import (
	create_ws_heartbeat_response,
)
from exceptions.websocket import WebSocketManagerException
from schemas.api.ws.response import (
	WebSocketResponse,
	WebSocketResponseType,
)
from shared.ids import generate_uuid_str
from shared.time import get_utc_datetime_now

_MAX_QUEUE_SIZE = 333
_HEARTBEAT_INTERVAL_SECONDS = 30
_QUEUE_PUT_TIMEOUT_SECONDS = 5
_SEND_TIMEOUT_SECONDS = 10
_CLOSE_TIMEOUT_SECONDS = 5

_logger = logging.getLogger(__name__)


class WebSocketManager:
	"""Own delivery tasks and activity for one connection.

	The controller accepts and reads the socket. Only the sender
	task writes response messages; close may send a close frame.
	"""

	def __init__(
		self,
		user_id: str,
		connection_id: str,
		websocket: WebSocket,
		request_id: str | None = None,
	) -> None:
		"""Prepare a bounded queue without starting tasks."""
		self.user_id = user_id
		self.connection_id = connection_id
		self.websocket = websocket
		self.request_id = request_id or generate_uuid_str()
		self.created_at = get_utc_datetime_now()
		self.last_message_at = self.created_at
		self._message_queue: asyncio.Queue[WebSocketResponse] = (
			asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
		)
		self._is_closed = asyncio.Event()
		self._close_complete = asyncio.Event()
		self._sender_task: asyncio.Task[None] | None = None
		self._heartbeat_task: asyncio.Task[None] | None = None

	@property
	def is_closed(self) -> bool:
		"""Report whether shutdown has begun."""
		return self._is_closed.is_set()

	def record_message(
		self, request_id: str | None = None
	) -> None:
		"""
		Record an incoming non-heartbeat application message.
		"""
		if not self.is_closed:
			self.last_message_at = get_utc_datetime_now()
			if request_id is not None:
				self.request_id = request_id

	def start(self) -> None:
		"""
		Start delivery and heartbeats once in the running loop.
		"""
		if self.is_closed:
			raise self._exception(
				'A closed connection cannot be restarted.',
				'start',
			)
		if self._sender_task is not None:
			return
		loop = asyncio.get_running_loop()
		self._sender_task = loop.create_task(
			self._send_queued_messages()
		)
		self._heartbeat_task = loop.create_task(
			self._heartbeat_loop()
		)

	async def close(
		self, code: int = 1000, reason: str = 'Normal closure'
	) -> None:
		"""
		Discard pending output and await task and socket cleanup.
		"""
		current = asyncio.current_task()
		tasks = (self._sender_task, self._heartbeat_task)
		if self.is_closed:
			# Avoid waiting for cancellation of the current task.
			if current not in tasks:
				await self._close_complete.wait()
			return
		self._is_closed.set()
		self._message_queue.shutdown(immediate=True)
		try:
			pending = [
				task
				for task in tasks
				if task is not None and task is not current
			]
			for task in pending:
				task.cancel()
			await asyncio.gather(
				*pending, return_exceptions=True
			)
		finally:
			try:
				async with asyncio.timeout(
					_CLOSE_TIMEOUT_SECONDS
				):
					await self.websocket.close(
						code=code, reason=reason
					)
			except Exception:
				self._log_exception(
					'Failed to close socket.', 'close'
				)
			finally:
				self._close_complete.set()

	async def send_message(
		self, response: WebSocketResponse
	) -> bool:
		"""Enqueue output; return acceptance, not client receipt.

		Close slow connections if queue space stays unavailable.
		Log unexpected enqueue failures and drop the item.
		Stamp a copied envelope with the current request ID so
		later state changes cannot relabel already queued output.
		"""
		if self.is_closed:
			return False
		response = response.model_copy(
			update={
				'meta': response.meta.model_copy(
					update={'request_id': self.request_id}
				),
			}
		)
		try:
			async with asyncio.timeout(
				_QUEUE_PUT_TIMEOUT_SECONDS
			):
				await self._message_queue.put(response)
			return True
		except asyncio.QueueShutDown:
			return False
		except TimeoutError:
			self._log_exception(
				'Outbound queue remained full.',
				'enqueue',
				response.meta.request_id,
			)
			await self.close(1013, 'Outbound queue exhausted')
		except Exception:
			self._log_exception(
				'Failed to enqueue response.',
				'enqueue',
				response.meta.request_id,
			)
		return False

	async def _heartbeat_loop(self) -> None:
		"""
		Queue periodic application heartbeats through the sender.
		"""
		try:
			while not self.is_closed:
				response = create_ws_heartbeat_response(
					payload='ping',
				)
				if not await self.send_message(response):
					if not self.is_closed:
						await self.close(
							1011, 'Heartbeat failed'
						)
					return
				await asyncio.sleep(_HEARTBEAT_INTERVAL_SECONDS)
		except asyncio.CancelledError:
			raise
		except Exception:
			self._log_exception('Heartbeat failed.', 'heartbeat')
			await self.close(1011, 'Heartbeat failed')

	async def _send_queued_messages(self) -> None:
		"""
		Read queued responses and write them to the socket in
		order.
		"""
		try:
			while not self.is_closed:
				response = await self._message_queue.get()
				try:
					async with asyncio.timeout(
						_SEND_TIMEOUT_SECONDS
					):
						await self.websocket.send_json(
							response.model_dump(mode='json')
						)
					if (
						response.type
						!= WebSocketResponseType.HEARTBEAT
					):
						self.last_message_at = (
							get_utc_datetime_now()
						)
				except TimeoutError:
					self._log_exception(
						'Response delivery timed out.',
						'send',
						response.meta.request_id,
					)
					await self.close(
						1013, 'Response delivery timed out'
					)
					return
				except Exception:
					self._log_exception(
						'Failed to deliver response.',
						'send',
						response.meta.request_id,
					)
					await self.close(
						1011, 'Response delivery failed'
					)
					return
				finally:
					self._message_queue.task_done()
		except asyncio.QueueShutDown:
			return
		except asyncio.CancelledError:
			raise
		except Exception:
			self._log_exception('Sender failed.', 'send')
			await self.close(1011, 'Response delivery failed')

	def _exception(
		self,
		message: str,
		operation: str,
		request_id: str | None = None,
	) -> WebSocketManagerException:
		"""
		Attach the connection and relevant request identifiers.
		"""
		return WebSocketManagerException(
			message=message,
			operation=operation,
			connection_id=self.connection_id,
			user_id=self.user_id,
			request_id=(
				request_id
				if request_id is not None
				else self.request_id
			),
		)

	def _log_exception(
		self,
		message: str,
		operation: str,
		request_id: str | None = None,
	) -> None:
		"""Log failures with structured connection context."""
		error = self._exception(message, operation, request_id)
		_logger.error(
			'%s',
			error,
			extra={
				'connection_id': error.connection_id,
				'user_id': error.user_id,
				'request_id': error.request_id,
				'operation': error.operation,
			},
			exc_info=True,
		)
