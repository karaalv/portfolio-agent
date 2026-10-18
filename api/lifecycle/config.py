"""Configuration for the API lifecycle"""

import sys
from os import getenv
from time import perf_counter

from api.lifecycle.environment import load_environment_variables
from api.lifecycle.logging import stop_component
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
from shared.logging import LogStyle, log_info, rich_print
from shared.logging.context import log_properties


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
		'staging',
		'production',
	}:
		start_posthog_client()
	component = 'mongodb'
	try:
		await start_mongo_client()
		component = 'openai'
		start_openai_client()
		component = 'websocket_registry'
		await start_websocket_registry()
	except Exception as exc:
		exc.__dict__['lifecycle_component'] = component
		raise

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


async def stop_api_lifecycle(
	*,
	shutdown_failed: bool = False,
	shutdown_started: float | None = None,
):
	"""Close sockets before shutting down service clients."""
	rich_print(
		message='Stopping Portfolio Backend...',
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)
	started = (
		shutdown_started
		if shutdown_started is not None
		else perf_counter()
	)
	try:
		await stop_component(
			stop_websocket_registry, 'websocket_registry'
		)
	finally:
		try:
			await stop_component(stop_openai_client, 'openai')
		finally:
			try:
				await stop_component(stop_mongo_client, 'mongodb')
			finally:
				log_info(
					'server_stopped',
					log_properties(
						'server_stopped',
						duration_seconds=perf_counter() - started,
						status='failed'
						if shutdown_failed
						or sys.exception() is not None
						else 'completed',
					),
				)
				await stop_component(stop_posthog_client, 'posthog')

	# Log successful shutdown
	rich_print(
		message='Portfolio Backend stopped successfully.',
		style=LogStyle.INFO,
		prefix='[API LIFECYCLE]',
	)
