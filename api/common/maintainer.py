"""
This module contains a maintenance class
used to clean up old data and manage
application state.
"""

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.memory.main import delete_memory
from common.utils import TerminalColors, get_datetime
from database.mongodb.main import get_collection
from users.database import delete_user


class Maintainer:
	"""
	A class that handles the maintenance
	tasks for the application, this includes:
	- Cleaning up old data
	"""

	def __init__(self):
		# Scheduler setup
		self.scheduler = AsyncIOScheduler(timezone=timezone.utc)
		self.scheduler.add_job(self.clean_up, 'interval', days=1)
		# Logging
		self.start_time = get_datetime()
		# Constants
		self.retention_time = 10  # days

		# Start the scheduler
		self.scheduler.start()

		print(
			f'{TerminalColors.green}'
			f'Maintainer started'
			f'{TerminalColors.reset}'
			f'{TerminalColors.yellow}'
			f' Timestamp: {datetime.now(timezone.utc)}'
			f'{TerminalColors.reset}'
		)

	async def clean_up(self):
		try:
			# Implement the cleanup logic here
			user_collection = get_collection('users')
			cutoff = (
				datetime.now(timezone.utc) - timedelta(days=self.retention_time)
			).isoformat() + 'Z'

			pipeline = [
				{'$match': {'last_active': {'$lt': cutoff}}},
				{'$project': {'_id': 0, 'user_id': 1}},
			]
			cursor = await user_collection.aggregate(pipeline)
			result = await cursor.to_list(length=None)
			stale_ids = [item['user_id'] for item in result]

			# Clear state data
			for user_id in stale_ids:
				await delete_memory(user_id)
				await delete_user(user_id)

			print(
				f'{TerminalColors.green}'
				f'Successfully cleaned up stale user data'
				f'{TerminalColors.reset}'
				f'{TerminalColors.yellow}'
				f' Timestamp: {datetime.now(timezone.utc)}'
				f'{TerminalColors.reset}'
			)
		except Exception as e:
			print(
				f'{TerminalColors.red}'
				f'Error occurred during cleanup'
				f'{TerminalColors.reset}'
				f'{TerminalColors.yellow}'
				f' Timestamp: {datetime.now(timezone.utc)}'
				f'{TerminalColors.reset}'
				f' Error: {e}'
			)
