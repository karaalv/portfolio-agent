"""Build typed WebSocket responses with shared API metadata."""

from schemas.agent.streaming.stream_manager import (
	StreamManagerItem,
)
from schemas.api.shared.metadata import ApiResponseMetaData
from schemas.api.ws.response import (
	WebSocketAgentDeltaResponse,
	WebSocketAgentEndResponse,
	WebSocketAgentStartResponse,
	WebSocketAgentThinkingCaptionsResponse,
	WebSocketErrorResponse,
	WebSocketHeartbeatResponse,
	WebSocketSetUserTokenResponse,
	WebSocketToolResponse,
	WebSocketWarningResponse,
)
from shared.ids import generate_uuid_str
from shared.time import get_utc_datetime_now


def create_ws_heartbeat_response(
	payload: str,
	message: str = 'Heartbeat',
) -> WebSocketHeartbeatResponse:
	"""Build a heartbeat response with its typed payload."""
	return WebSocketHeartbeatResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_agent_start_response(
	payload: str,
	message: str = 'Agent start',
) -> WebSocketAgentStartResponse:
	"""Build a agent_start response with its typed payload."""
	return WebSocketAgentStartResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_agent_end_response(
	payload: str,
	message: str = 'Agent end',
) -> WebSocketAgentEndResponse:
	"""Build a agent_end response with its typed payload."""
	return WebSocketAgentEndResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_agent_delta_response(
	payload: StreamManagerItem,
	message: str = 'Agent delta',
) -> WebSocketAgentDeltaResponse:
	"""Build a agent_delta response with its typed payload."""
	return WebSocketAgentDeltaResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_tool_message_response(
	payload: set[str],
	message: str = 'Tool message',
) -> WebSocketToolResponse:
	"""Build a tool_message response with its typed payload."""
	return WebSocketToolResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_agent_thinking_captions_response(
	payload: list[str],
	message: str = 'Agent thinking captions',
) -> WebSocketAgentThinkingCaptionsResponse:
	"""Build ordered captions describing planned retrieval."""
	return WebSocketAgentThinkingCaptionsResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_set_user_token_response(
	payload: str,
	message: str = 'Set user token',
) -> WebSocketSetUserTokenResponse:
	"""Build a set_user_token response with its typed payload."""
	return WebSocketSetUserTokenResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_warning_response(
	payload: str,
	message: str = 'Warning',
) -> WebSocketWarningResponse:
	"""Build a warning response with its typed payload."""
	return WebSocketWarningResponse(
		meta=_create_metadata(True, message),
		payload=payload,
	)


def create_ws_error_response(
	payload: str,
	message: str = 'Error',
) -> WebSocketErrorResponse:
	"""Build a error response with its typed payload."""
	return WebSocketErrorResponse(
		meta=_create_metadata(False, message),
		payload=payload,
	)


def _create_metadata(
	success: bool, message: str
) -> ApiResponseMetaData:
	"""Create fallback metadata before the manager stamps its ID."""
	return ApiResponseMetaData(
		request_id=generate_uuid_str(),
		success=success,
		message=message,
		timestamp=get_utc_datetime_now(),
	)
