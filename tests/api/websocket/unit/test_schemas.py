"""Validate protocol payload mappings and response helpers."""

from collections.abc import Callable
from datetime import datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from api.websocket.helpers import responses
from schemas.agent.streaming.stream_manager import (
	StreamManagerItem,
	StreamManagerItemType,
)
from schemas.api.ws.request import (
	WebSocketRequest,
	WebSocketRequestType,
)
from schemas.api.ws.response import WebSocketResponse

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('kind', ['agent_message', 'heartbeat'])
def test_request_accepts_text(kind: str) -> None:
	"""Both client message types accept string payloads."""
	request = WebSocketRequest.model_validate(
		{
			'type': kind,
			'payload': 'hello',
		}
	)
	assert request.type == kind
	assert request.payload == 'hello'
	assert request.request_id is None


def test_request_preserves_client_id() -> None:
	"""Accept an optional client correlation string."""
	request = WebSocketRequest(
		type=WebSocketRequestType.AGENT_MESSAGE,
		payload='hello',
		request_id='client-request',
	)
	assert request.request_id == 'client-request'


@pytest.mark.parametrize(
	'data',
	[
		{'type': 'unknown', 'payload': 'hello'},
		{'type': 'agent_message', 'payload': {'text': 'hello'}},
		{'type': 'heartbeat'},
		{
			'type': 'heartbeat',
			'payload': 'pong',
			'request_id': 1,
		},
	],
)
def test_request_rejects_invalid_envelopes(data: object) -> None:
	"""
	Unknown types, missing payloads and objects are rejected.
	"""
	with pytest.raises(ValidationError):
		WebSocketRequest.model_validate(data)


@pytest.mark.parametrize(
	'factory, kind, success',
	[
		(
			responses.create_ws_heartbeat_response,
			'heartbeat',
			True,
		),
		(
			responses.create_ws_agent_start_response,
			'agent_start',
			True,
		),
		(
			responses.create_ws_agent_end_response,
			'agent_end',
			True,
		),
		(
			responses.create_ws_set_user_token_response,
			'set_user_token',
			True,
		),
		(responses.create_ws_warning_response, 'warning', True),
		(responses.create_ws_error_response, 'error', False),
	],
)
def test_text_helpers_create_valid_envelopes(
	factory: Callable[[str, str], WebSocketResponse],
	kind: str,
	success: bool,
) -> None:
	"""Helpers generate identity and preserve payload metadata."""
	response = factory('payload', 'Description')
	assert response.type == kind
	assert response.payload == 'payload'
	assert response.meta.request_id
	assert (
		factory('next', 'Next').meta.request_id
		!= response.meta.request_id
	)
	assert response.meta.message == 'Description'
	assert response.meta.success is success
	offset = response.meta.timestamp.utcoffset()
	assert offset is not None
	assert offset.total_seconds() == 0
	parsed = TypeAdapter(WebSocketResponse).validate_json(
		response.model_dump_json()
	)
	assert parsed == response


def test_agent_and_tool_helpers_round_trip() -> None:
	"""
	Structured stream items and unique tool names survive JSON.
	"""
	item = StreamManagerItem(
		type=StreamManagerItemType.TEXT,
		user_id='user',
		memory_id='memory',
		sequence_number=1,
		payload='Hello',
	)
	response = responses.create_ws_agent_delta_response(item)
	parsed = TypeAdapter(WebSocketResponse).validate_json(
		response.model_dump_json()
	)
	assert parsed.type == 'agent_delta'
	assert parsed.payload == item
	tool = responses.create_ws_tool_message_response(
		{'fetch_context'}
	)
	assert tool.model_dump(mode='json')['payload'] == [
		'fetch_context'
	]
	assert TypeAdapter(WebSocketResponse).validate_json(
		tool.model_dump_json()
	).payload == {'fetch_context'}


@pytest.mark.parametrize(
	'kind, payload',
	[
		('agent_delta', 'plain text'),
		('tool_message', 'plain text'),
		('agent_thinking_captions', 'plain text'),
		('heartbeat', ['ping']),
		('warning', {'text': 'notice'}),
		('unknown', 'text'),
	],
)
def test_response_discriminator_rejects_wrong_payload(
	kind: str,
	payload: object,
) -> None:
	"""Payloads cannot be accepted under an incompatible type."""
	with pytest.raises(ValidationError):
		TypeAdapter(WebSocketResponse).validate_python(
			{
				'type': kind,
				'payload': payload,
				'meta': {
					'request_id': 'request',
					'success': True,
					'message': 'message',
					'timestamp': datetime.now().isoformat(),
				},
			}
		)


def test_thinking_captions_preserve_order() -> None:
	"""Round-trip planner captions as an ordered JSON array."""
	captions = ["Checking Alvin's education", 'Exploring his work']
	response = responses.create_ws_agent_thinking_captions_response(
		captions
	)
	parsed = TypeAdapter(WebSocketResponse).validate_json(
		response.model_dump_json()
	)
	assert parsed.type == 'agent_thinking_captions'
	assert parsed.payload == captions
