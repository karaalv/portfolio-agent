"""Start and stop the API's background maintenance routines."""

from api.maintenance.user_data_pruner import UserDataPruner


class MaintenanceManager:
	"""Own maintenance routine instances for one API lifespan."""

	def __init__(self) -> None:
		self.user_data_pruner = UserDataPruner()

	def start(self) -> None:
		"""Start all maintenance routines."""
		self.user_data_pruner.start()

	async def stop(self) -> None:
		"""Stop all maintenance routines."""
		await self.user_data_pruner.stop()
