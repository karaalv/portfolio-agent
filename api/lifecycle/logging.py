"""Report API lifecycle outcomes before telemetry is shut down."""

from collections.abc import Awaitable, Callable
from os import getenv
from time import perf_counter

from agent.config.agent import AGENT_TOOL_RECURSION_LIMIT
from api.config.websocket import (
	MAX_CONTENT_SIZE_BYTES,
	MAX_INPUT_TOKENS,
)
from openai_client.models import OpenAILanguageModel
from posthog_client.error_tracking import report_exception
from shared.logging import log_info
from shared.logging.context import log_properties


def capture_lifecycle_failure(
	exc: Exception,
	operation: str,
	component: str,
) -> None:
	"""Reserve CRITICAL for failed application startup."""
	report_exception(
		exc,
		f'server_{operation}_failed',
		{
			'operation': operation,
			'component': getattr(
				exc, 'lifecycle_component', component
			),
		},
		severity='critical' if operation == 'startup' else 'error',
	)


async def stop_component(
	stop: Callable[[], Awaitable[None]],
	component: str,
) -> None:
	"""Report cleanup failures while preserving their propagation."""
	try:
		await stop()
	except Exception as exc:
		capture_lifecycle_failure(exc, 'shutdown', component)
		raise


def log_server_started(version: str, started: float) -> None:
	"""Emit readiness with an explicit allowlist of safe settings."""
	log_info(
		'server_started',
		log_properties(
			'server_started',
			service_version=version,
			port=getenv('PORTFOLIO_AGENT_PORT'),
			model=OpenAILanguageModel.GPT_6_1_SOL.value,
			max_content_size_bytes=MAX_CONTENT_SIZE_BYTES,
			max_input_tokens=MAX_INPUT_TOKENS,
			tool_recursion_limit=AGENT_TOOL_RECURSION_LIMIT,
			telemetry_enabled=getenv('PORTFOLIO_AGENT_ENV')
			in {'development', 'production'},
			duration_seconds=perf_counter() - started,
		),
	)
