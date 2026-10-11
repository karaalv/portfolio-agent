"""Pair each server message type with its valid payload."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from schemas.agent.streaming.stream_manager import (
	StreamManagerItem,
)
from schemas.api.shared.metadata import ApiResponseMetaData


class WebSocketResponseType(StrEnum):
	"""Supported server message types."""

	HEARTBEAT = 'heartbeat'
	AGENT_START = 'agent_start'
	AGENT_END = 'agent_end'
	AGENT_DELTA = 'agent_delta'
	TOOL_MESSAGE = 'tool_message'
	SET_USER_TOKEN = 'set_user_token'
	WARNING = 'warning'
	ERROR = 'error'


class _ResponseEnvelope[T](BaseModel):
	"""Share metadata and payload fields between variants."""

	meta: ApiResponseMetaData
	payload: T


class WebSocketHeartbeatResponse(_ResponseEnvelope[str]):
	"""Carry the payload for a heartbeat message."""

	type: Literal[WebSocketResponseType.HEARTBEAT] = (
		WebSocketResponseType.HEARTBEAT
	)


class WebSocketAgentStartResponse(_ResponseEnvelope[str]):
	"""Carry the payload for an agent_start message."""

	type: Literal[WebSocketResponseType.AGENT_START] = (
		WebSocketResponseType.AGENT_START
	)


class WebSocketAgentEndResponse(_ResponseEnvelope[str]):
	"""Carry the payload for an agent_end message."""

	type: Literal[WebSocketResponseType.AGENT_END] = (
		WebSocketResponseType.AGENT_END
	)


class WebSocketAgentDeltaResponse(
	_ResponseEnvelope[StreamManagerItem]
):
	"""Carry the payload for an agent_delta message."""

	type: Literal[WebSocketResponseType.AGENT_DELTA] = (
		WebSocketResponseType.AGENT_DELTA
	)


class WebSocketToolResponse(_ResponseEnvelope[set[str]]):
	"""Carry the payload for a tool_message message."""

	type: Literal[WebSocketResponseType.TOOL_MESSAGE] = (
		WebSocketResponseType.TOOL_MESSAGE
	)


class WebSocketSetUserTokenResponse(_ResponseEnvelope[str]):
	"""Carry the payload for a set_user_token message."""

	type: Literal[WebSocketResponseType.SET_USER_TOKEN] = (
		WebSocketResponseType.SET_USER_TOKEN
	)


class WebSocketWarningResponse(_ResponseEnvelope[str]):
	"""Carry the payload for a warning message."""

	type: Literal[WebSocketResponseType.WARNING] = (
		WebSocketResponseType.WARNING
	)


class WebSocketErrorResponse(_ResponseEnvelope[str]):
	"""Carry the payload for an error message."""

	type: Literal[WebSocketResponseType.ERROR] = (
		WebSocketResponseType.ERROR
	)


type WebSocketResponse = Annotated[
	WebSocketHeartbeatResponse
	| WebSocketAgentStartResponse
	| WebSocketAgentEndResponse
	| WebSocketAgentDeltaResponse
	| WebSocketToolResponse
	| WebSocketSetUserTokenResponse
	| WebSocketWarningResponse
	| WebSocketErrorResponse,
	Field(discriminator='type'),
]
