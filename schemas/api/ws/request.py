"""Validate messages received from portfolio clients."""

from enum import StrEnum

from pydantic import BaseModel


class WebSocketRequestType(StrEnum):
	"""Supported client message types."""

	AGENT_MESSAGE = 'agent_message'
	HEARTBEAT = 'heartbeat'


class WebSocketRequest(BaseModel):
	"""Carry text for either an agent message or heartbeat."""

	type: WebSocketRequestType
	payload: str
