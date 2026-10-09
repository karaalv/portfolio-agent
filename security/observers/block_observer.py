"""Prune access blocks after their minimum blocking period."""

import asyncio

from security.monitoring.blocked.config import (
	BLOCK_CLEANUP_INTERVAL_SECONDS,
)
from security.monitoring.blocked.deletion import (
	prune_expired_blocks,
)
from shared.logging import LogStyle, rich_print


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

		rich_print(
			message='Starting block observer...',
			style=LogStyle.INFO,
			prefix='security.observers',
		)

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
			rich_print(
				message='Stopping block observer...',
				style=LogStyle.INFO,
				prefix='security.observers',
			)

	async def run_once(self) -> None:
		"""Delete expired block records from MongoDB."""
		await prune_expired_blocks()

	async def _run(self) -> None:
		"""Prune at startup and every six hours thereafter."""
		while True:
			try:
				await self.run_once()
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				rich_print(
					f'Block maintenance failed: {exc}',
					style=LogStyle.ERROR,
					prefix='security.observers',
				)
			await asyncio.sleep(BLOCK_CLEANUP_INTERVAL_SECONDS)
