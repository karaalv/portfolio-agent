"""Configure MongoDB connections for the selected environment."""

import os

from pymongo import AsyncMongoClient

from common.utils import TerminalColors

# --- Databases and Collections ---

DATABASES: list[str] = [
	'application',
	'analytics',
]
COLLECTIONS: list[str] = [
	'users',
	'messages',
	'corpus',
	'monitoring',
]
database_mappings: dict[str, str] = {
	# Application Database
	'users': 'application',
	'messages': 'application',
	'corpus': 'application',
	'monitoring': 'application',
}

# --- Connection Management ---

MONGO_CLIENT: AsyncMongoClient | None = None


def resolve_cluster() -> str:
	"""Return the MongoDB URI for the selected environment."""
	env = os.getenv('PORTFOLIO_AGENT_ENV')

	if env == 'testing':
		return str(os.getenv('MONGO_DEVELOPMENT'))
	elif env == 'production':
		return str(os.getenv('MONGO_PRODUCTION'))
	else:
		return str(os.getenv('MONGO_DEVELOPMENT'))


async def connect_mongo() -> bool:
	"""Connect to MongoDB and return whether its ping succeeds."""
	global MONGO_CLIENT

	try:
		if MONGO_CLIENT is None:
			MONGO_CLIENT = AsyncMongoClient(
				resolve_cluster(),
			)
			await MONGO_CLIENT.aconnect()

		print('Connecting to MongoDB...')
		response = await MONGO_CLIENT.admin.command('ping')

		if response.get('ok') != 1:
			raise Exception(
				'Ping failed, connection not established.'
			)

		print(
			f'{TerminalColors.green}'
			f'Successfully connected to MongoDB'
			f'{TerminalColors.reset}'
			f' client: '
			f'{TerminalColors.yellow}'
			f'{os.getenv("PORTFOLIO_AGENT_ENV")}'
			f'{TerminalColors.reset}'
			f' cluster'
		)
		return True
	except Exception as e:
		print(
			f'{TerminalColors.red}'
			f'Failed to connect to MongoDB: '
			f'{TerminalColors.reset}'
			f'{e}'
		)
		return False


async def close_mongo() -> bool:
	"""
	Closes the MongoDB connection.

	Returns:
		bool: True if connection is closed,
		False otherwise.
	"""
	global MONGO_CLIENT

	if MONGO_CLIENT is None:
		print(
			f'{TerminalColors.yellow}'
			f'Mongo client is None, no closure'
			f'{TerminalColors.reset}'
		)
		return False

	try:
		await MONGO_CLIENT.close()
		MONGO_CLIENT = None
		print(
			f'{TerminalColors.green}'
			f'Successfully closed MongoDB connection'
			f'{TerminalColors.reset}'
		)
		return True
	except Exception as e:
		print(
			f'{TerminalColors.red}'
			f'Failed to close MongoDB connection: '
			f'{TerminalColors.reset}'
			f'{e}'
		)
		return False


async def is_mongo_connected() -> bool:
	"""
	Checks if the MongoDB client is connected.

	Returns:
		bool: True if connected, False otherwise.
	"""
	global MONGO_CLIENT

	if MONGO_CLIENT is None:
		return False

	try:
		response = await MONGO_CLIENT.admin.command('ping')

		if response.get('ok') == 1:
			return True
		else:
			print(
				f'{TerminalColors.red}'
				f'MongoDB connection check failed: '
				f'{TerminalColors.reset}'
				f'Ping response not OK'
			)
			return False
	except Exception as e:
		print(
			f'{TerminalColors.red}'
			f'MongoDB connection check failed: '
			f'{TerminalColors.reset}'
			f'{e}'
		)
		return False


def get_mongo_client() -> AsyncMongoClient:
	"""
	Returns the MongoDB client.

	Returns:
		AsyncMongoClient: The MongoDB client instance.
	"""
	global MONGO_CLIENT

	if MONGO_CLIENT is None:
		raise Exception(
			'MongoDB client is not initialised. '
			'Call connect_mongo() first.'
		)

	return MONGO_CLIENT


if __name__ == '__main__':
	import asyncio

	from dotenv import load_dotenv

	load_dotenv(override=True, dotenv_path=os.path.abspath('.env'))

	async def main():
		await connect_mongo()
		await close_mongo()

	asyncio.run(main())
