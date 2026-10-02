"""
Stored conversation entries for anonymous portfolio visitors.
"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from shared.time.get import get_utc_datetime_now


class AgentMemorySource(StrEnum):
	"""
	Participants whose messages are
	stored as conversation memory.
	"""

	USER = 'user'
	AGENT = 'agent'


class AgentMemory(BaseModel):
	"""
	One visitor or assistant message
	in application.memories.
	"""

	memory_id: str
	user_id: str
	memory_source: AgentMemorySource
	created_at: datetime = Field(default_factory=get_utc_datetime_now)
	content: str

	@field_validator('created_at')
	@classmethod
	def normalise_created_at(cls, value: datetime) -> datetime:
		"""Normalise BSON dates, including naive UTC dates, to UTC."""
		if value.tzinfo is None:
			return value.replace(tzinfo=timezone.utc)
		return value.astimezone(timezone.utc)
