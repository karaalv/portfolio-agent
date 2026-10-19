"""Reconcile daily usage and prune inactive usage records."""

import asyncio
from datetime import timedelta
from time import perf_counter
from typing import Any

from posthog_client.tracing import start_span
from security.monitoring.usage.config import USAGE_RETENTION_DAYS
from security.monitoring.usage.deletion import (
	prune_inactive_usage,
)
from security.monitoring.usage.update import reset_daily_usage
from security.observers._logging import capture_maintenance_failure
from shared.logging import log_info
from shared.logging.context import log_properties
from shared.time import get_utc_datetime_now


class UsageObserver:
	"""Own the daily usage maintenance task for one app."""

	def __init__(self) -> None:
		"""Prepare an observer without starting its task."""
		self._task: asyncio.Task[None] | None = None
		self._progress: dict[str, Any] = {}

	def start(self) -> None:
		"""Start once on the application's running event loop."""
		if self._task is None or self._task.done():
			loop = asyncio.get_running_loop()
			self._task = loop.create_task(self._run())

	async def stop(self) -> None:
		"""Cancel maintenance and wait for it to finish."""
		if self._task is None:
			return
		self._task.cancel()
		try:
			await self._task
		except asyncio.CancelledError:
			pass
		finally:
			self._task = None

	async def run_once(self) -> None:
		"""Reset older days and prune inactive records."""
		with start_span('maintenance.usage.prune'):
			started = perf_counter()
			self._progress = {'operation': 'reset_daily_usage'}
			reset_count = await reset_daily_usage()
			self._progress = {
				'operation': 'prune_inactive_usage',
				'records_reset': reset_count,
			}
			deleted_count = await prune_inactive_usage()
			log_info(
				'usage_maintenance_completed',
				log_properties(
					'usage_maintenance_completed',
					records_reset=reset_count,
					records_deleted=deleted_count,
					cutoff=(
						get_utc_datetime_now()
						- timedelta(days=USAGE_RETENTION_DAYS)
					).isoformat(),
					duration_seconds=perf_counter() - started,
				),
			)

	async def _run(self) -> None:
		"""Reconcile at startup, then at each UTC midnight."""
		while True:
			try:
				await self.run_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				capture_maintenance_failure(
					exc,
					'usage_observer',
					getattr(self, '_progress', {}),
				)
			await asyncio.sleep(_seconds_until_utc_midnight())


def _seconds_until_utc_midnight() -> float:
	"""Calculate the next UTC boundary from the current time."""
	now = get_utc_datetime_now()
	next_midnight = now.replace(
		hour=0, minute=0, second=0, microsecond=0
	) + timedelta(days=1)
	return (next_midnight - now).total_seconds()
