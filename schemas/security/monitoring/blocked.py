"""Describe persisted IP and user access blocks."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class BlockedEntity(StrEnum):
	"""Identify the IP address or visitor denied access."""

	IP = 'ip'
	USER = 'user'


class BlockedRecord(BaseModel):
	"""Deny access until the record is explicitly deleted."""

	entity: BlockedEntity
	entity_id: str = Field(min_length=1)
	blocked_at: datetime
	blocked_until: datetime
	reason: str = Field(min_length=1)

	@field_validator('blocked_at', 'blocked_until')
	@classmethod
	def normalise_datetime(cls, value: datetime) -> datetime:
		"""Interpret naive BSON dates as UTC."""
		if value.tzinfo is None:
			return value.replace(tzinfo=UTC)
		return value.astimezone(UTC)
