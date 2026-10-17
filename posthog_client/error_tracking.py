"""Capture exceptions with explicit application identity."""

from os import getenv
from typing import Any

from posthog_client.config import get_posthog_client


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
