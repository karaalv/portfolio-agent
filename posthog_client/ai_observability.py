"""Attribute model calls to agent turns and socket AI sessions."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from os import getenv
from typing import Any, TypedDict

from posthog import Posthog

from posthog_client.config import get_posthog_client
from shared.logging import log_error


@dataclass(frozen=True)
class AIContext:
	"""Keep replay sessions distinct from socket AI sessions."""

	user_id: str | None = None
	session_id: str | None = None
	ai_trace_id: str | None = None
	ai_session_id: str | None = None


_context: ContextVar[AIContext | None] = ContextVar(
	'ai_observability', default=None
)


@contextmanager
def ai_observability_context(
	context: AIContext,
) -> Generator[None]:
	"""Share attribution with nested calls and restore on exit."""
	token = _context.set(context)
	try:
		yield
	finally:
		_context.reset(token)


def get_ai_posthog_client() -> Posthog:
	"""Use active telemetry or return a disabled client."""
	if getenv('PORTFOLIO_AGENT_ENV') in {
		'development',
		'staging',
		'production',
	}:
		return get_posthog_client()
	return Posthog(
		project_api_key='disabled',
		disabled=True,
		sync_mode=True,
		enable_exception_autocapture=False,
	)


class _GenerationOptions(TypedDict):
	posthog_distinct_id: str | None
	posthog_trace_id: str | None
	posthog_properties: dict[str, Any]
	posthog_privacy_mode: bool


def generation_options_from_context() -> _GenerationOptions:
	"""Build wrapper arguments from the current turn context."""
	context = _context.get() or AIContext()
	properties = {
		'$session_id': context.session_id,
		'$ai_session_id': context.ai_session_id,
		'environment': getenv('PORTFOLIO_AGENT_ENV'),
	}
	return {
		'posthog_distinct_id': context.user_id,
		'posthog_trace_id': context.ai_trace_id,
		'posthog_properties': {
			key: value
			for key, value in properties.items()
			if value is not None
		},
		'posthog_privacy_mode': False,
	}


def capture_agent_trace(
	*,
	user_input: str,
	output_text: str,
	duration_seconds: float,
	started_at: datetime,
	outcome: str,
	turn_id: str,
	error: BaseException | None = None,
) -> None:
	"""Capture turn I/O without allowing telemetry to break chat."""
	if getenv('PORTFOLIO_AGENT_ENV') not in {
		'development',
		'staging',
		'production',
	}:
		return
	context = _context.get()
	if context is None or context.ai_trace_id is None:
		return
	properties: dict[str, Any] = {
		'$ai_trace_id': context.ai_trace_id,
		'$ai_span_name': 'Portfolio chat',
		'$ai_input_state': [{'role': 'user', 'content': user_input}],
		'$ai_output_state': (
			[{'role': 'assistant', 'content': output_text}]
			if output_text
			else []
		),
		'$ai_latency': duration_seconds,
		'$ai_is_error': outcome != 'completed',
		'outcome': outcome,
		'turn_id': turn_id,
		**generation_options_from_context()['posthog_properties'],
	}
	if outcome != 'completed':
		properties['$ai_error'] = (
			type(error).__name__ if error is not None else outcome
		)
	try:
		get_posthog_client().capture(
			'$ai_trace',
			distinct_id=context.user_id,
			properties=properties,
			timestamp=started_at,
		)
	except Exception as capture_error:
		log_error(
			'telemetry_capture_failed',
			{
				'capture_boundary': 'agent_trace',
				'exception_class': type(capture_error).__name__,
			},
		)
