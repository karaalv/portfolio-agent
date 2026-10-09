"""Start and stop security services for one API lifespan."""

from security.lifecycle import (
	start_security_client,
	stop_security_client,
)
from security.observers.block_observer import BlockObserver
from security.observers.usage_observer import UsageObserver
from shared.logging import LogStyle, rich_print


class SecurityManager:
	"""Own observers and the security client lifecycle."""

	def __init__(self) -> None:
		"""Prepare observers without starting tasks."""
		self.usage_observer = UsageObserver()
		self.block_observer = BlockObserver()

	async def start(self) -> None:
		"""Start services and undo partial startup on failure."""
		rich_print(
			message='Starting security services...',
			style=LogStyle.INFO,
			prefix='[SECURITY MANAGER]',
		)
		try:
			await start_security_client()
			self.usage_observer.start()
			self.block_observer.start()
		except BaseException:
			await self.stop()
			raise

	async def stop(self) -> None:
		"""Attempt cleanup of every security service."""
		rich_print(
			message='Stopping security services...',
			style=LogStyle.INFO,
			prefix='[SECURITY MANAGER]',
		)
		try:
			await self.block_observer.stop()
		finally:
			try:
				await self.usage_observer.stop()
			finally:
				await stop_security_client()
