"""Prune access blocks after their minimum blocking period."""

import asyncio
from time import perf_counter

from security.monitoring.blocked.config import (
	BLOCK_CLEANUP_INTERVAL_SECONDS,
)
from security.monitoring.blocked.deletion import (
	prune_expired_blocks,
)
from security.observers._logging import capture_maintenance_failure
from shared.logging import log_info
from shared.logging.context import log_properties


class BlockObserver:
	"""Own periodic block cleanup for the sole app instance."""

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
		"""Delete expired block records from MongoDB."""
		started = perf_counter()
		deleted_count = await prune_expired_blocks()
		log_info(
			'block_cleanup_completed',
			log_properties(
				'block_cleanup_completed',
				blocks_deleted=deleted_count,
				duration_seconds=perf_counter() - started,
			),
		)

	async def _run(self) -> None:
		"""Prune at startup and every six hours thereafter."""
		while True:
			try:
				await self.run_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				capture_maintenance_failure(exc, 'block_observer')
			await asyncio.sleep(BLOCK_CLEANUP_INTERVAL_SECONDS)
