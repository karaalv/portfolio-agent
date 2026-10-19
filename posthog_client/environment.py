"""Read and validate PostHog client environment settings."""

from os import getenv

from exceptions.posthog import PostHogException


def require_environment_variable(name: str) -> str:
	"""Return a trimmed setting or reject missing/blank values."""
	value = getenv(name)
	if not value or not value.strip():
		raise PostHogException(
			message=(
				f"Environment variable '{name}' must not be empty."
			),
			module='posthog_client.environment',
			operation='require_environment_variable',
		)
	return value.strip()
