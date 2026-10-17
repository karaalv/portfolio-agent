"""Configuration for the API lifecycle"""

from os import getenv

from api.lifecycle.environment import load_environment_variables
from api.websocket import (
	start_websocket_registry,
	stop_websocket_registry,
)
from database.mongodb.config import (
	start_mongo_client,
	stop_mongo_client,
)
from openai_client.config import (
	start_openai_client,
	stop_openai_client,
)
from posthog_client.config import (
	start_posthog_client,
	stop_posthog_client,
)
from shared.logging import LogStyle, rich_print


async def start_api_lifecycle():
	"""
	Load the environment and start clients and socket tracking.
	"""
	rich_print(
		message='Starting Portfolio Backend...',
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)
	load_environment_variables()
	if getenv('PORTFOLIO_AGENT_ENV') in {
		'development',
		'production',
	}:
		start_posthog_client()
	await start_mongo_client()
	start_openai_client()
	await start_websocket_registry()

	# Log successful startup
	env = getenv('PORTFOLIO_AGENT_ENV')
	port = getenv('PORTFOLIO_AGENT_PORT')
	rich_print(
		message=(
			f'Portfolio Backend started successfully '
			f'in {env} environment on port {port}.'
		),
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)


async def stop_api_lifecycle():
	"""Close sockets before shutting down service clients."""
	rich_print(
		message='Stopping Portfolio Backend...',
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)
	try:
		await stop_websocket_registry()
	finally:
		try:
			await stop_openai_client()
		finally:
			try:
				await stop_mongo_client()
			finally:
				await stop_posthog_client()

	# Log successful shutdown
	rich_print(
		message='Portfolio Backend stopped successfully.',
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)
