"""Describe daily usage and registered WebSocket connections."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from shared.time import get_utc_datetime_now


class UsageEntity(StrEnum):
	"""Identify an IP address or authenticated visitor."""

	IP = 'ip'
	USER = 'user'


class UsageScope(StrEnum):
	"""Identify a daily allowance or connection allowance."""

	DAILY_REQUESTS = 'daily_requests'
	DAILY_TOKENS = 'daily_tokens'
	ACTIVE_WS = 'active_ws'


@dataclass(slots=True)
class UsagePolicy:
	"""Set the maximum allowed value before blocking."""

	scope: UsageScope
	limit: int


class UsageStatistics(BaseModel):
	"""Store current daily counters and connection IDs."""

	entity: UsageEntity
	entity_id: str = Field(min_length=1)
	usage_day: str = Field(
		default_factory=lambda: (
			get_utc_datetime_now().date().isoformat()
		),
		description='UTC counter date in YYYY-MM-DD format.',
	)
	daily_requests: int = Field(default=0, ge=0)
	daily_input_tokens: int = Field(default=0, ge=0)
	active_ws_connections: list[str] = Field(
		default_factory=list
	)
	last_request_at: datetime = Field(
		default_factory=get_utc_datetime_now
	)

	@field_validator('usage_day')
	@classmethod
	def normalise_usage_day(cls, value: str) -> str:
		"""Normalise the counter date for comparisons."""
		return date.fromisoformat(value).isoformat()

	@field_validator('last_request_at')
	@classmethod
	def normalise_datetime(cls, value: datetime) -> datetime:
		"""Interpret naive BSON dates as UTC."""
		if value.tzinfo is None:
			return value.replace(tzinfo=UTC)
		return value.astimezone(UTC)
