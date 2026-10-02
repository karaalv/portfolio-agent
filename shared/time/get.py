"""Retrieve the current time as a UTC datetime."""

from datetime import UTC, datetime


def get_utc_datetime_now() -> datetime:
	"""Return the current timezone-aware UTC datetime."""
	return datetime.now(UTC)
