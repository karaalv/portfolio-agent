"""Report tool failures independently of verbose terminal output."""

from posthog_client.error_tracking import report_exception
from shared.logging import log_warning
from shared.logging.context import log_properties


def log_tool_rejected(
	user_id: str,
	tool_name: str | None,
	call_id: str | None,
	connection_id: str | None,
	posthog_session_id: str | None,
	reason: str,
) -> None:
	"""Retain rejection classification without model arguments."""
	log_warning(
		'tool_call_rejected',
		log_properties(
			'tool_call_rejected',
			user_id=user_id,
			posthog_session_id=posthog_session_id,
			tool_name=tool_name,
			call_id=call_id,
			connection_id=connection_id,
			reason=reason,
		),
	)


def capture_tool_failure(
	exc: Exception,
	user_id: str,
	tool_name: str | None,
	call_id: str | None,
	connection_id: str | None,
	posthog_session_id: str | None,
) -> None:
	"""Capture unexpected exceptions before returning a fallback."""
	report_exception(
		exc,
		'tool_call_failed',
		{
			'tool_name': tool_name,
			'call_id': call_id,
			'connection_id': connection_id,
		},
		user_id=user_id,
		posthog_session_id=posthog_session_id,
	)
