"""Capture exceptions with explicit application identity."""

from os import getenv
from typing import Any, Literal

from exceptions.core import PortfolioAgentException
from posthog_client.config import get_posthog_client
from shared.logging import log_critical, log_error, log_warning
from shared.logging.context import log_properties


def capture_exception(
	exc: Exception,
	user_id: str | None,
	properties: dict[str, Any],
) -> None:
	"""Skip testing telemetry; otherwise delegate to PostHog."""
	if getenv('PORTFOLIO_AGENT_ENV') == 'testing':
		return
	client = get_posthog_client()
	kwargs: dict[str, Any] = {'properties': properties}
	if user_id is not None:
		kwargs['distinct_id'] = user_id
	client.capture_exception(exc, **kwargs)


def report_exception(
	exc: Exception,
	event_name: str,
	properties: dict[str, Any],
	*,
	user_id: str | None = None,
	posthog_session_id: str | None = None,
	severity: Literal['warning', 'error', 'critical'] = 'error',
) -> None:
	"""Report once while preserving the original failure."""
	if getattr(exc, '_portfolio_reported', False):
		return
	exc.__dict__['_portfolio_reported'] = True
	metadata = log_properties(
		event_name,
		user_id=user_id,
		posthog_session_id=posthog_session_id,
		exception_class=type(exc).__name__,
		exception_message=str(exc),
		**properties,
	)
	if isinstance(exc, PortfolioAgentException):
		metadata.update(
			scope=exc.scope,
			module=exc.module,
			operation=exc.operation,
		)
	log_metadata = dict(metadata)
	if 'module' in log_metadata:
		log_metadata['exception_module'] = log_metadata.pop('module')
	if severity == 'warning':
		log_warning(event_name, log_metadata)
	elif severity == 'error':
		log_error(event_name, log_metadata, exc=exc)
	elif severity == 'critical':
		log_critical(event_name, log_metadata, exc=exc)
	try:
		capture_exception(exc, user_id, metadata)
	except Exception as capture_error:
		log_error(
			'telemetry_capture_failed',
			log_properties(
				'telemetry_capture_failed',
				capture_boundary=event_name,
				exception_class=type(capture_error).__name__,
			),
		)
