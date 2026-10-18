"""Attribute model calls to agent turns and socket AI sessions."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from os import getenv
from typing import Any, TypedDict

from posthog import Posthog

from posthog_client.config import get_posthog_client


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
	"""Use the active client or a disabled SDK outside dev/prod."""
	if getenv('PORTFOLIO_AGENT_ENV') in {'development', 'production'}:
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
