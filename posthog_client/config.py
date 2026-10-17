"""Manage the process-local PostHog client."""

import asyncio

from posthog import Posthog

from exceptions.posthog import PostHogException
from posthog_client.environment import require_environment_variable
from shared.logging import LogStyle, rich_print

_posthog_client: Posthog | None = None


def start_posthog_client() -> None:
	"""Create the client once after validating its settings."""
	global _posthog_client
	if _posthog_client is not None:
		return
	api_key = require_environment_variable('POSTHOG_API_KEY')
	host = require_environment_variable('POSTHOG_HOST')
	_posthog_client = Posthog(
		project_api_key=api_key,
		host=host,
		enable_exception_autocapture=False,
	)
	rich_print(
		'PostHog client started successfully.',
		style=LogStyle.SUCCESS,
		prefix='posthog_client.config',
	)


async def stop_posthog_client() -> None:
	"""Detach the client and drain its queue off the event loop."""
	global _posthog_client
	client = _posthog_client
	if client is None:
		return
	_posthog_client = None
	await asyncio.to_thread(client.shutdown)
	rich_print(
		'PostHog client stopped successfully.',
		style=LogStyle.SUCCESS,
		prefix='posthog_client.config',
	)


def get_posthog_client() -> Posthog:
	"""Return the started client or raise a lifecycle error."""
	if _posthog_client is None:
		raise PostHogException(
			message='PostHog client is not started.',
			module='posthog_client.config',
			operation='get_posthog_client',
		)
	return _posthog_client
