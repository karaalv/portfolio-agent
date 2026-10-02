"""Manage the process-local OpenAI client."""

from os import getenv

from openai import AsyncOpenAI

from exceptions.openai import OpenAIException
from shared.logging import LogStyle, rich_print

# --- Configuration ---

# Global OpenAI client
_openai_client: AsyncOpenAI | None = None

# --- Connection Management ---


def start_openai_client() -> None:
	"""Create the OpenAI client after environment loading."""
	global _openai_client
	if _openai_client is None:
		api_key = getenv('OPENAI_KEY')
		if not api_key:
			raise OpenAIException(
				message='OPENAI_KEY environment variable is not set.',
				module='openai_client/config.py',
				operation='start_openai_client',
			)
		_openai_client = AsyncOpenAI(api_key=api_key)

		rich_print(
			'OpenAI client started successfully.',
			style=LogStyle.SUCCESS,
			prefix='openai_client.config',
		)


async def stop_openai_client() -> None:
	"""Close the current OpenAI client and clear its reference."""
	global _openai_client
	if _openai_client is None:
		return

	await _openai_client.close()
	set_openai_client(None)

	rich_print(
		'OpenAI client stopped successfully.',
		style=LogStyle.SUCCESS,
		prefix='openai_client.config',
	)


# --- Client Access ---


def get_openai_client() -> AsyncOpenAI:
	"""Return the started client or raise if it is unavailable."""
	if _openai_client is None:
		raise OpenAIException(
			message='OpenAI client is not started.',
			module='openai_client/config.py',
			operation='get_openai_client',
		)
	return _openai_client


def set_openai_client(client: AsyncOpenAI | None) -> None:
	"""Replace the process-local client, primarily for tests."""
	global _openai_client
	_openai_client = client
