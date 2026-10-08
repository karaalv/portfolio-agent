"""Manage rate limiters owned by one app and event loop."""

import asyncio
from datetime import timedelta

from aiolimiter import AsyncLimiter

from schemas.security.ratelimit import (
	RateLimiter,
	ResourceAccessor,
	ResourceScope,
)
from security.ratelimit.config import get_rate_limit_config
from shared.logging import LogStyle, rich_print
from shared.time import get_utc_datetime_now


class RateLimitStore:
	"""Keep caller allowances isolated within an app instance."""

	_cleanup_interval_seconds = 12 * 60 * 60 # 12 hours
	_retention_period = timedelta(days=3)

	def __init__(self) -> None:
		"""Create the store and start background cleanup."""
		loop = asyncio.get_running_loop()
		self._limiters: dict[str, RateLimiter] = {}
		self._limiters_lock = asyncio.Lock()
		self._cleanup_task: asyncio.Task[None] | None = (
			loop.create_task(self._cleanup_loop())
		)

	async def stop(self) -> None:
		"""Cancel background cleanup and await its completion."""
		if self._cleanup_task is None:
			return
		self._cleanup_task.cancel()
		try:
			await self._cleanup_task
		except asyncio.CancelledError:
			pass
		finally:
			self._cleanup_task = None

	async def get_all_limiters(self) -> dict[str, RateLimiter]:
		"""Copy the dictionary, sharing its limiter objects."""
		async with self._limiters_lock:
			return self._limiters.copy()

	async def get_limiter(
		self,
		resource_scope: ResourceScope,
		resource_accessor: ResourceAccessor,
		identifier_value: str,
	) -> AsyncLimiter:
		"""Retrieve or create a limiter atomically."""
		key = _get_limiter_key(
			resource_scope, resource_accessor, identifier_value
		)
		async with self._limiters_lock:
			if key not in self._limiters:
				config = get_rate_limit_config(
					resource_scope, resource_accessor
				)
				self._limiters[key] = RateLimiter(
					resource_scope=resource_scope,
					resource_accessor=resource_accessor,
					identifier_value=identifier_value,
					limiter=AsyncLimiter(
						config.max_rate, config.time_period
					),
				)
			record = self._limiters[key]
			record.last_accessed_at = get_utc_datetime_now()
			return record.limiter

	async def delete_limiter(
		self,
		resource_scope: ResourceScope,
		resource_accessor: ResourceAccessor,
		identifier_value: str,
	) -> None:
		"""Remove a caller's limiter if it exists."""
		key = _get_limiter_key(
			resource_scope, resource_accessor, identifier_value
		)
		async with self._limiters_lock:
			self._limiters.pop(key, None)

	async def delete_limiters_by_keys(
		self, limiter_keys: list[str]
	) -> None:
		"""Remove stored keys, ignoring missing entries."""
		async with self._limiters_lock:
			for key in limiter_keys:
				self._limiters.pop(key, None)

	async def prune_once(self) -> None:
		"""Remove limiters unused for more than three days."""
		async with self._limiters_lock:
			cutoff = (
				get_utc_datetime_now() - self._retention_period
			)
			keys = [
				key
				for key, record in self._limiters.items()
				if record.last_accessed_at < cutoff
			]
			for key in keys:
				del self._limiters[key]

	async def _cleanup_loop(self) -> None:
		"""Prune every twelve hours until cancelled."""
		while True:
			await asyncio.sleep(self._cleanup_interval_seconds)
			try:
				await self.prune_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				rich_print(
					f'Rate limiter cleanup failed: {exc}',
					style=LogStyle.ERROR,
					prefix='security.ratelimit',
				)


def _get_limiter_key(
	resource_scope: ResourceScope,
	resource_accessor: ResourceAccessor,
	identifier_value: str,
) -> str:
	"""Build a key from scope, caller kind and identity."""
	if not identifier_value.strip():
		raise ValueError('identifier_value must not be empty.')
	return (
		f'{resource_scope.value}:'
		f'{resource_accessor.value}:'
		f'{identifier_value}'
	)
