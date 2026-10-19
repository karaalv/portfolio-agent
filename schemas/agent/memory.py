"""
Canonical stored API items and metadata for model replay.
"""

from datetime import datetime, timezone

from openai.types.responses import ResponseInputItemParam
from pydantic import BaseModel, Field, field_validator

from shared.ids import generate_uuid_str
from shared.time.get import get_utc_datetime_now


class AgentMemory(BaseModel):
	"""One API payload with ownership and order metadata."""

	user_id: str
	memory_id: str = Field(
		default_factory=generate_uuid_str,
		description=(
			'Unique identifier for each artefact stored '
			'in the memory collection.'
		),
	)
	turn_id: str = Field(
		description=(
			'Identifier shared by one user message, any optional '
			'tool calls and their outputs, and the agent response.'
		)
	)
	created_at: datetime = Field(default_factory=get_utc_datetime_now)
	sequence: int = Field(ge=0)
	payload: ResponseInputItemParam

	@field_validator('created_at')
	@classmethod
	def normalise_created_at(cls, value: datetime) -> datetime:
		"""Normalise aware and naive BSON dates to UTC."""
		if value.tzinfo is None:
			return value.replace(tzinfo=timezone.utc)
		return value.astimezone(timezone.utc)
