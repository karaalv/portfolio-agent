"""
This module contains the schemas used for
the API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from common.utils import get_timestamp

# --- General Schemas ---


class MetaData(BaseModel):
	"""
	Metadata schema for API responses.
	"""

	success: bool = Field(
		...,
		description='Indicates if the request was successful.',
	)

	message: str = Field(
		...,
		description='A message providing additional '
		'information about the request, '
		'such as success or error details.',
	)

	timestamp: str = Field(
		default_factory=get_timestamp,
		description='The timestamp of the request in ISO 8601 format.',
	)


# --- HTTP Responses ---


class APIResponse(BaseModel):
	"""
	Base schema for API responses.
	"""

	metadata: MetaData = Field(
		..., description='Metadata about the API response.'
	)

	data: Optional[Any] = Field(
		None,
		description='The actual data returned by the API.',
	)


# --- Socket Data ---


class SocketResponse(BaseModel):
	"""
	Base schema for websocket
	responses.
	"""

	metadata: MetaData = Field(
		...,
		description='Metadata about the websocket response.',
	)
	type: str = Field(
		...,
		description='The type of data passed inthe socket response.',
	)
	data: Optional[Any] = Field(
		None,
		description='The actual data returned by the websocket.',
	)


class SocketMessage(BaseModel):
	"""
	Schema for messages sent from
	websocket clients.
	"""

	type: str = Field(..., description='The type of message being sent.')
	data: Optional[str] = Field(
		None,
		description='The actual data being sent in the message.',
	)
