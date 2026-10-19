"""
Schemas used for defining the structure and validation
of data related to the Stream Manager.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from shared.ids import generate_uuid_str
from shared.time import get_utc_datetime_now

# --- Enums ---


class EventStreamState(StrEnum):
	MESSAGE = 'message'
	FUNCTION_CALL = 'function_call'
	IDLE = 'idle'


class StreamManagerItemType(StrEnum):
	TEXT = 'text'


# --- Models ---


class StreamManagerItem(BaseModel):
	stream_id: str = Field(default_factory=generate_uuid_str)
	timestamp: datetime = Field(default_factory=get_utc_datetime_now)
	type: StreamManagerItemType
	user_id: str
	memory_id: str
	sequence_number: int
	payload: str


class StreamManagerFunctionCall(BaseModel):
	call_id: str
	tool_name: str
	tool_args: str = Field(
		description='Raw JSON arguments validated by the tool.'
	)
