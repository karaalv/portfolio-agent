"""Remove data for anonymous users inactive for seven days."""

import asyncio
from datetime import datetime, timedelta, timezone
from itertools import batched
from time import perf_counter
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from posthog_client.error_tracking import report_exception
from shared.logging import log_info
from shared.logging.context import log_properties


class UserDataPruner:
	"""Prune inactive users and their chat messages once per day."""

	_batch_size = 30

	def __init__(self) -> None:
		self._interval_seconds = 24 * 60 * 60  # 24 hours
		self._inactive_user_ids: set[str] = set()
		self._task: asyncio.Task[None] | None = None
		self._progress: dict[str, Any] = {}

	def start(self) -> None:
		"""
		Start the periodic pruning task on
		the running event loop.
		"""
		if self._task is None or self._task.done():
			self._task = asyncio.create_task(self._run())

	async def stop(self) -> None:
		"""Cancel the pruning task and wait for it to finish."""
		if self._task is None:
			return

		self._task.cancel()
		try:
			await self._task
		except asyncio.CancelledError:
			pass
		finally:
			self._task = None

	async def prune_once(self) -> None:
		"""Delete inactive user records and their messages."""
		cutoff = datetime.now(timezone.utc) - timedelta(days=7)
		started = perf_counter()
		self._progress = {
			'cutoff': cutoff.isoformat(),
			'candidate_count': 0,
			'users_deleted': 0,
			'messages_deleted': 0,
			'skipped_users': 0,
		}
		users = get_collection(MongoDBCollection.USERS)
		messages = get_collection(MongoDBCollection.MEMORIES)

		ids = await self._get_inactive_users(users, cutoff)

		self._progress['candidate_count'] = len(ids)

		for batch in batched(tuple(ids), self._batch_size):
			results = await asyncio.gather(
				*(
					self._delete_user_data(
						user_id, cutoff, users, messages
					)
					for user_id in batch
				),
				return_exceptions=True,
			)
			for result in results:
				if isinstance(result, BaseException):
					raise result

		log_info(
			'user_data_prune_completed',
			log_properties(
				'user_data_prune_completed',
				**self._progress,
				duration_seconds=perf_counter() - started,
			),
		)

	async def _get_inactive_users(
		self, users: AsyncCollection, cutoff: datetime
	) -> set[str]:
		"""Return pending IDs, including newly inactive users."""
		cursor = users.find(
			{'last_active_at': {'$lt': cutoff}},
			{'_id': 0, 'user_id': 1},
		)
		async for document in cursor:
			user_id = document.get('user_id')
			if isinstance(user_id, str):
				self._inactive_user_ids.add(user_id)
		return self._inactive_user_ids

	async def _delete_user_data(
		self,
		user_id: str,
		cutoff: datetime,
		users: AsyncCollection,
		messages: AsyncCollection,
	) -> None:
		"""Delete one inactive user's messages and record."""
		inactive_user = await users.find_one(
			{
				'user_id': user_id,
				'last_active_at': {'$lt': cutoff},
			},
			{'_id': 1},
		)
		if inactive_user is None:
			self._inactive_user_ids.discard(user_id)
			self._progress['skipped_users'] += 1
			return

		message_result = await messages.delete_many(
			{'user_id': user_id}
		)
		self._progress['messages_deleted'] += (
			message_result.deleted_count
		)
		user_result = await users.delete_one(
			{
				'user_id': user_id,
				'last_active_at': {'$lt': cutoff},
			}
		)
		self._progress['users_deleted'] += user_result.deleted_count
		if user_result.deleted_count == 0:
			self._progress['skipped_users'] += 1
		self._inactive_user_ids.discard(user_id)

	async def _run(self) -> None:
		"""Prune at startup and every 24 hours thereafter."""
		while True:
			try:
				await self.prune_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				self._capture_exception(exc)
			await asyncio.sleep(self._interval_seconds)

	def _capture_exception(self, exc: Exception) -> None:
		"""Include actual partial progress in failed pruning runs."""
		report_exception(
			exc,
			'maintenance_failed',
			{
				'job': 'user_data_pruner',
				**self._progress,
			},
		)
