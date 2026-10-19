"""Report maintenance task failures without visitor context."""

from typing import Any

from posthog_client.error_tracking import report_exception


def capture_maintenance_failure(
	exc: Exception, job: str, properties: dict[str, Any] | None = None
) -> None:
	"""Retain partial progress when a recurring job fails."""
	report_exception(
		exc, 'maintenance_failed', {'job': job, **(properties or {})}
	)
