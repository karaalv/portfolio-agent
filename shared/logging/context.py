"""Build stable telemetry attributes without changing identity."""

from os import getenv
from typing import Any

from shared.time import get_utc_datetime_now


def log_properties(
	event_name: str,
	*,
	user_id: str | None = None,
	posthog_session_id: str | None = None,
	**metadata: Any,
) -> dict[str, Any]:
	"""Include PostHog's default log identity/session join keys."""
	properties = {
		'event_name': event_name,
		'timestamp': get_utc_datetime_now().isoformat(),
		'environment': getenv('PORTFOLIO_AGENT_ENV'),
		**metadata,
	}
	if user_id is not None:
		properties.update(user_id=user_id, posthogDistinctId=user_id)
	if posthog_session_id is not None:
		properties.update(
			posthog_session_id=posthog_session_id,
			sessionId=posthog_session_id,
		)
		properties['$session_id'] = posthog_session_id
	return {
		key: value
		for key, value in properties.items()
		if value is not None
	}
