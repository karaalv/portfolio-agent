"""Track local connections and close inactive managers."""

import asyncio
from datetime import timedelta

from fastapi import WebSocket, WebSocketException

from api.websocket.manager import WebSocketManager
from exceptions.security import EntityBlockedException
from exceptions.websocket import WebSocketRegistryException
from posthog_client.error_tracking import report_exception
from schemas.api.ws.response import WebSocketResponse
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.monitoring.usage import UsageEntity, UsageScope
from security.monitoring.blocked.enforcement import apply_24h_block
from security.monitoring.usage.config import get_usage_policy
from shared.logging import log_info
from shared.logging.context import log_properties
from shared.time import get_utc_datetime_now

_INACTIVE_CONNECTION_SECONDS = 60 * 60
_PRUNE_INTERVAL_SECONDS = 60 * 15


class WebSocketRegistry:
	"""Own managers by user and connection within one process.

	Locks protect tracking state. Socket sends and closure take
	place outside the lock so other users can continue working.
	"""

	def __init__(self) -> None:
		"""
		Prepare tracking state without starting background work.
		"""
		self._registry: dict[str, dict[str, WebSocketManager]] = {}
		self._lock = asyncio.Lock()
		self._blocking_users: set[str] = set()
		self._pruner_task: asyncio.Task[None] | None = None
		self._is_stopped = False

	def start(self) -> None:
		"""
		Start periodic cleanup once in the running event loop.
		"""
		if self._is_stopped:
			raise WebSocketRegistryException(
				'A stopped registry cannot be restarted.',
				'start',
			)
		if self._pruner_task is None:
			self._pruner_task = asyncio.create_task(
				self._prune_loop()
			)

	async def stop(self) -> None:
		"""
		Reject new connections, stop cleanup and close managers.
		"""
		async with self._lock:
			self._is_stopped = True
		if self._pruner_task is not None:
			self._pruner_task.cancel()
			await asyncio.gather(
				self._pruner_task, return_exceptions=True
			)
		await self.close_all_connections(
			reason='Server shutting down', close_code=1001
		)

	async def has_user(self, user_id: str) -> bool:
		"""Report whether a user has tracked connections."""
		async with self._lock:
			return user_id in self._registry

	async def has_connection(
		self, user_id: str, connection_id: str
	) -> bool:
		"""Report whether the supplied connection is tracked."""
		return (
			await self.get_connection(user_id, connection_id)
			is not None
		)

	async def get_connection(
		self, user_id: str, connection_id: str
	) -> WebSocketManager | None:
		"""
		Find a manager without holding a lock for later I/O.
		"""
		async with self._lock:
			return self._registry.get(user_id, {}).get(connection_id)

	async def count_connections(self, user_id: str) -> int:
		"""Count tracked connections for one user."""
		async with self._lock:
			return len(self._registry.get(user_id, {}))

	async def add_connection(
		self,
		user_id: str,
		connection_id: str,
		websocket: WebSocket,
		request_id: str | None = None,
		posthog_session_id: str | None = None,
	) -> WebSocketManager:
		"""Track an accepted socket and start its manager.

		Reject duplicate keys rather than leaking an old manager.
		Block on the fifth connection using the user usage policy.
		"""
		async with self._lock:
			if self._is_stopped:
				raise WebSocketRegistryException(
					'The registry has stopped.', 'add_connection'
				)
			connections = self._registry.get(user_id, {})
			if connection_id in connections:
				raise WebSocketRegistryException(
					'The connection is already registered.',
					'add_connection',
				)
			blocking = user_id in self._blocking_users
			limit = get_usage_policy(
				UsageEntity.USER, UsageScope.ACTIVE_WS
			).limit
			exceeded = len(connections) >= limit
			if not blocking and not exceeded:
				manager = WebSocketManager(
					user_id,
					connection_id,
					websocket,
					request_id,
					posthog_session_id=posthog_session_id,
				)
				manager.start()
				self._registry.setdefault(user_id, {})[
					connection_id
				] = manager
				return manager
			if not blocking:
				self._blocking_users.add(user_id)

		# Keep database writes and socket closure outside the lock.
		if blocking:
			await websocket.close(
				code=1008, reason='Access is blocked.'
			)
			raise WebSocketException(
				code=1008, reason='Access is blocked.'
			)
		try:
			try:
				await apply_24h_block(
					BlockedEntity.USER,
					user_id,
					'Active WebSocket connection limit exceeded.',
				)
			except EntityBlockedException as exc:
				raise WebSocketException(
					code=1008, reason='Access is blocked.'
				) from exc
			finally:
				try:
					await self.remove_user_connections(
						user_id,
						reason='Access is blocked.',
						close_code=1008,
					)
				finally:
					await websocket.close(
						code=1008, reason='Access is blocked.'
					)
		finally:
			async with self._lock:
				self._blocking_users.discard(user_id)

	async def remove_connection(
		self,
		user_id: str,
		connection_id: str,
		reason: str = 'Normal closure',
		close_code: int = 1000,
	) -> None:
		"""Remove tracking state, then close the connection."""
		async with self._lock:
			connections = self._registry.get(user_id, {})
			manager = connections.pop(connection_id, None)
			if not connections:
				self._registry.pop(user_id, None)
		if manager is not None:
			await manager.close(code=close_code, reason=reason)

	async def remove_user_connections(
		self,
		user_id: str,
		reason: str = 'Normal closure',
		close_code: int = 1000,
	) -> None:
		"""
		Remove and close every tracked connection for one user.
		"""
		await self.remove_users_connections(
			[user_id], reason=reason, close_code=close_code
		)

	async def remove_users_connections(
		self,
		user_ids: list[str],
		reason: str = 'Normal closure',
		close_code: int = 1000,
	) -> None:
		"""
		Remove selected users atomically, then close their
		sockets.
		"""
		async with self._lock:
			managers = [
				manager
				for user_id in user_ids
				for manager in self._registry.pop(
					user_id, {}
				).values()
			]
		await self._close_managers(managers, close_code, reason)

	async def close_all_connections(
		self,
		reason: str = 'Normal closure',
		close_code: int = 1000,
	) -> None:
		"""
		Clear tracked connections and close the removed managers.
		"""
		async with self._lock:
			managers = [
				manager
				for connections in self._registry.values()
				for manager in connections.values()
			]
			self._registry.clear()
		await self._close_managers(managers, close_code, reason)

	async def send_connection(
		self,
		user_id: str,
		connection_id: str,
		message: WebSocketResponse,
	) -> bool:
		"""
		Queue output on one tracked connection, if still open.
		"""
		manager = await self.get_connection(user_id, connection_id)
		if manager is None:
			return False
		return await manager.send_message(message)

	async def _prune_loop(self) -> None:
		"""
		Periodically clean idle or already closed connections.
		"""
		while True:
			await asyncio.sleep(_PRUNE_INTERVAL_SECONDS)
			try:
				await self._prune_inactive_connections()
			except Exception as exc:
				self._capture_exception(exc, 'prune_connections')

	def _capture_exception(
		self, exc: Exception, operation: str
	) -> None:
		"""Report registry task failures outside request handlers."""
		report_exception(
			exc,
			'websocket_registry_failed',
			{'operation': operation, 'job': 'websocket_registry'},
		)

	async def _prune_inactive_connections(self) -> None:
		"""
		Remove stale managers under lock and close them outside
		it.
		"""
		cutoff = get_utc_datetime_now() - timedelta(
			seconds=_INACTIVE_CONNECTION_SECONDS
		)
		managers: list[WebSocketManager] = []
		async with self._lock:
			for user_id, connections in list(self._registry.items()):
				for connection_id, manager in list(
					connections.items()
				):
					if (
						manager.is_closed
						or manager.last_message_at <= cutoff
					):
						managers.append(
							connections.pop(connection_id)
						)
				if not connections:
					del self._registry[user_id]
		await self._close_managers(
			managers, 1001, 'Connection inactive'
		)
		log_info(
			'websocket_cleanup_completed',
			log_properties(
				'websocket_cleanup_completed',
				closed_connections=len(managers),
			),
		)

	async def _close_managers(
		self,
		managers: list[WebSocketManager],
		code: int,
		reason: str,
	) -> None:
		"""
		Close detached managers concurrently outside state locks.
		"""
		closing = asyncio.gather(
			*(
				manager.close(code=code, reason=reason)
				for manager in managers
			)
		)
		try:
			await asyncio.shield(closing)
		except asyncio.CancelledError:
			# Detached managers must finish closing before exit.
			await closing
			raise
