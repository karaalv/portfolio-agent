"""Configure MongoDB connections for the selected environment."""

from os import getenv

from pymongo import AsyncMongoClient

from exceptions.mongodb import MongoDBException
from shared.logging import LogStyle, rich_print

# --- Configuration ---

# Global MongoDB client
_mongo_client: AsyncMongoClient | None = None

# --- Connection Management ---


async def start_mongo_client() -> None:
	"""Starts the global MongoDB client."""
	global _mongo_client
	if _mongo_client is None:
		uri = getenv('MONGODB_URI')
		if not uri:
			raise MongoDBException(
				message=(
					'MONGODB_URI environment variable is not set.'
				),
				module='database/mongodb/config.py',
				operation='start_mongo_client',
			)

		# Try to start client asynchronously
		try:
			rich_print(
				'Starting MongoDB client...',
				style=LogStyle.INFO,
				prefix='mongodb.config',
			)
			_mongo_client = AsyncMongoClient(uri)
			await _mongo_client.aconnect()
			rich_print(
				'MongoDB client started successfully.',
				style=LogStyle.SUCCESS,
				prefix='mongodb.config',
			)
		except Exception as e:
			raise MongoDBException(
				message=f'Failed to start MongoDB client: {e}',
				module='database/mongodb/config.py',
				operation='start_mongo_client',
			) from e


async def stop_mongo_client() -> None:
	"""Stops the global MongoDB client."""
	global _mongo_client
	if _mongo_client is not None:
		try:
			rich_print(
				'Stopping MongoDB client...',
				style=LogStyle.INFO,
				prefix='mongodb.config',
			)
			await _mongo_client.close()
			set_mongo_client(None)
			rich_print(
				'MongoDB client stopped successfully.',
				style=LogStyle.SUCCESS,
				prefix='mongodb.config',
			)
		except Exception as e:
			raise MongoDBException(
				message=f'Failed to stop MongoDB client: {e}',
				module='database/mongodb/config.py',
				operation='stop_mongo_client',
			) from e


async def is_mongo_connected() -> bool:
	"""Checks if the global MongoDB client is connected."""
	global _mongo_client
	if _mongo_client is None:
		return False
	try:
		await _mongo_client.admin.command('ping')
		return True
	except Exception:
		return False


# --- Client Access ---


def get_mongo_client() -> AsyncMongoClient:
	"""Returns the global MongoDB client."""
	if _mongo_client is None:
		raise MongoDBException(
			message='MongoDB client is not started.',
			module='database/mongodb/config.py',
			operation='get_mongo_client',
		)
	return _mongo_client


def set_mongo_client(client: AsyncMongoClient | None) -> None:
	"""Sets the global MongoDB client."""
	global _mongo_client
	_mongo_client = client
