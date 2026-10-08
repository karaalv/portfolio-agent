"""Reconcile daily usage and prune inactive usage records."""

import asyncio
from datetime import timedelta

from security.monitoring.usage.deletion import (
	prune_inactive_usage,
)
from security.monitoring.usage.update import reset_daily_usage
from shared.logging import LogStyle, rich_print
from shared.time import get_utc_datetime_now


class UsageObserver:
	"""Own the daily usage maintenance task for one app."""

	def __init__(self) -> None:
		"""Prepare an observer without starting its task."""
		self._task: asyncio.Task[None] | None = None

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
		await reset_daily_usage()
		await prune_inactive_usage()

	async def _run(self) -> None:
		"""Reconcile at startup, then at each UTC midnight."""
		while True:
			try:
				await self.run_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				rich_print(
					f'Usage maintenance failed: {exc}',
					style=LogStyle.ERROR,
					prefix='security.observers',
				)
			await asyncio.sleep(_seconds_until_utc_midnight())


def _seconds_until_utc_midnight() -> float:
	"""Calculate the next UTC boundary from the current time."""
	now = get_utc_datetime_now()
	next_midnight = now.replace(
		hour=0, minute=0, second=0, microsecond=0
	) + timedelta(days=1)
	return (next_midnight - now).total_seconds()
