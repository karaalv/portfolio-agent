"""
Frontend text message schemas derived from model memory.
Internal reasoning and tool payloads are excluded from chat.
"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from shared.time.get import get_utc_datetime_now


class AgentChatSource(StrEnum):
	"""Display sources; the API assistant maps to agent."""

	USER = 'user'
	AGENT = 'agent'


class AgentChatMemory(BaseModel):
	"""A display message without internal model artefacts."""

	memory_id: str
	user_id: str
	memory_source: AgentChatSource
	created_at: datetime = Field(default_factory=get_utc_datetime_now)
	content: str

	@field_validator('created_at')
	@classmethod
	def normalise_created_at(cls, value: datetime) -> datetime:
		"""Normalise aware and naive BSON dates to UTC."""
		if value.tzinfo is None:
			return value.replace(tzinfo=timezone.utc)
		return value.astimezone(timezone.utc)
