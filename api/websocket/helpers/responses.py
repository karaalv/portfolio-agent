"""Build typed WebSocket responses with shared API metadata."""

from schemas.agent.streaming.stream_manager import (
	StreamManagerItem,
)
from schemas.api.shared.metadata import ApiResponseMetaData
from schemas.api.ws.response import (
	WebSocketAgentEndResponse,
	WebSocketAgentResponse,
	WebSocketAgentStartResponse,
	WebSocketErrorResponse,
	WebSocketHeartbeatResponse,
	WebSocketSetUserTokenResponse,
	WebSocketToolResponse,
	WebSocketWarningResponse,
)
from shared.time import get_utc_datetime_now


def create_ws_heartbeat_response(
	request_id: str,
	payload: str,
	message: str = 'Heartbeat',
) -> WebSocketHeartbeatResponse:
	"""Build a heartbeat response with its typed payload."""
	return WebSocketHeartbeatResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_agent_start_response(
	request_id: str,
	payload: str,
	message: str = 'Agent start',
) -> WebSocketAgentStartResponse:
	"""Build a agent_start response with its typed payload."""
	return WebSocketAgentStartResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_agent_end_response(
	request_id: str,
	payload: str,
	message: str = 'Agent end',
) -> WebSocketAgentEndResponse:
	"""Build a agent_end response with its typed payload."""
	return WebSocketAgentEndResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_agent_response(
	request_id: str,
	payload: StreamManagerItem,
	message: str = 'Agent response',
) -> WebSocketAgentResponse:
	"""Build a agent_response response with its typed payload."""
	return WebSocketAgentResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_tool_message_response(
	request_id: str,
	payload: set[str],
	message: str = 'Tool message',
) -> WebSocketToolResponse:
	"""Build a tool_message response with its typed payload."""
	return WebSocketToolResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_set_user_token_response(
	request_id: str,
	payload: str,
	message: str = 'Set user token',
) -> WebSocketSetUserTokenResponse:
	"""Build a set_user_token response with its typed payload."""
	return WebSocketSetUserTokenResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_warning_response(
	request_id: str,
	payload: str,
	message: str = 'Warning',
) -> WebSocketWarningResponse:
	"""Build a warning response with its typed payload."""
	return WebSocketWarningResponse(
		meta=_create_metadata(request_id, True, message),
		payload=payload,
	)


def create_ws_error_response(
	request_id: str,
	payload: str,
	message: str = 'Error',
) -> WebSocketErrorResponse:
	"""Build a error response with its typed payload."""
	return WebSocketErrorResponse(
		meta=_create_metadata(request_id, False, message),
		payload=payload,
	)


def _create_metadata(
	request_id: str, success: bool, message: str
) -> ApiResponseMetaData:
	"""Timestamp a response without exposing connection state."""
	return ApiResponseMetaData(
		request_id=request_id,
		success=success,
		message=message,
		timestamp=get_utc_datetime_now(),
	)
