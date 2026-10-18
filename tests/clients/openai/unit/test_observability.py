"""Exercise the real PostHog wrapper without external services."""

import asyncio
import json
from contextlib import aclosing
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai.types.responses import ResponseCompletedEvent
from posthog import Posthog
from posthog.ai.openai import AsyncOpenAI
from pydantic import BaseModel

from openai_client import config, main
from posthog_client import ai_observability
from posthog_client.ai_observability import (
	AIContext,
	ai_observability_context,
	generation_options_from_context,
)

pytestmark = pytest.mark.unit


def response_payload(text='Hello'):
	"""Build a response payload with content and token counts."""
	return {
		'id': 'response',
		'object': 'response',
		'created_at': 1,
		'model': 'gpt-4o-mini',
		'status': 'completed',
		'parallel_tool_calls': True,
		'tool_choice': 'auto',
		'tools': [],
		'error': None,
		'incomplete_details': None,
		'output': [
			{
				'id': 'message',
				'type': 'message',
				'role': 'assistant',
				'status': 'completed',
				'content': [
					{
						'type': 'output_text',
						'text': text,
						'annotations': [],
					}
				],
			}
		],
		'usage': {
			'input_tokens': 10,
			'output_tokens': 2,
			'total_tokens': 12,
			'input_tokens_details': {'cached_tokens': 0},
			'output_tokens_details': {'reasoning_tokens': 0},
		},
	}


@pytest.fixture
async def wrapped(monkeypatch):
	"""Capture SDK events locally and simulate provider HTTP."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	posthog = Posthog('disabled', disabled=True, sync_mode=True)
	capture = Mock()
	monkeypatch.setattr(posthog, 'capture', capture)
	requests = []
	responses = []

	def transport(request):
		body = json.loads(request.content)
		requests.append(body)
		if request.url.path.endswith('/embeddings'):
			response = httpx.Response(
				200,
				json={
					'object': 'list',
					'model': body['model'],
					'data': [
						{
							'object': 'embedding',
							'index': 0,
							'embedding': [0.1, 0.2],
						}
					],
					'usage': {
						'prompt_tokens': 10,
						'total_tokens': 10,
					},
				},
			)
		elif body.get('stream'):
			payload = response_payload()
			events = [
				{
					'type': 'response.output_text.delta',
					'delta': 'Hello',
					'item_id': 'message',
					'output_index': 0,
					'content_index': 0,
					'sequence_number': 0,
				},
				{
					'type': 'response.completed',
					'response': payload,
					'sequence_number': 1,
				},
			]
			response = httpx.Response(
				200,
				headers={'content-type': 'text/event-stream'},
				content=''.join(
					'data: ' + json.dumps(event) + '\n\n'
					for event in events
				),
			)
		else:
			structured = (
				body.get('text', {}).get('format', {}).get('type')
				== 'json_schema'
			)
			response = httpx.Response(
				200,
				json=response_payload(
					'{"answer": "Hello"}' if structured else 'Hello'
				),
			)
		responses.append(response)
		return response

	client = AsyncOpenAI(
		api_key='test',
		posthog_client=posthog,
		max_retries=0,
		http_client=httpx.AsyncClient(
			transport=httpx.MockTransport(transport)
		),
	)
	monkeypatch.setattr(config, '_openai_client', client)
	for name in (
		'get_openai_semaphore',
		'get_openai_response_limiter',
		'get_openai_embedding_limiter',
	):
		monkeypatch.setattr(main, name, lambda: asyncio.Semaphore(10))
	monkeypatch.setattr(
		main, 'get_openai_response_timeout', lambda: 10
	)
	try:
		yield SimpleNamespace(
			client=client,
			capture=capture,
			requests=requests,
			responses=responses,
		)
	finally:
		await client.close()
		posthog.shutdown()


async def test_wrapped_stream_captures_once_on_terminal_break(
	wrapped,
):
	"""Retain SDK types, usage and context when closing the stream."""
	with ai_observability_context(
		AIContext('visitor', 'replay', 'turn-trace', 'socket')
	):
		async with aclosing(
			main.stream_agent_response(
				'system',
				[{'role': 'user', 'content': 'Hi'}],
			)
		) as events:
			async for event in events:
				if event.type == 'response.completed':
					assert isinstance(event, ResponseCompletedEvent)
					break
	wrapped.capture.assert_called_once()
	kwargs = wrapped.capture.call_args.kwargs
	assert kwargs['distinct_id'] == 'visitor'
	properties = kwargs['properties']
	assert properties['$ai_trace_id'] == 'turn-trace'
	assert properties['$ai_session_id'] == 'socket'
	assert properties['$session_id'] == 'replay'
	assert properties['$ai_input_tokens'] == 10
	assert properties['$ai_output_tokens'] == 2
	assert properties['$ai_input']
	assert properties['$ai_output_choices']
	assert wrapped.responses[0].is_closed
	assert not any(
		key.startswith('posthog') for key in wrapped.requests[0]
	)


class Answer(BaseModel):
	answer: str


async def test_text_parse_and_embedding_inherit_turn(wrapped):
	"""Tool-internal model calls keep attribution and return types."""
	with ai_observability_context(
		AIContext('visitor', 'replay', 'trace', 'socket')
	):
		assert await main.text_response('system', 'Hi') == 'Hello'
		parsed = await main.structured_response(
			'system', 'Hi', Answer
		)
		assert isinstance(parsed, Answer)
		assert parsed.answer == 'Hello'
		assert await main.get_embedding('Hi') == [0.1, 0.2]
	assert wrapped.capture.call_count == 3
	for call in wrapped.capture.call_args_list:
		assert call.kwargs['distinct_id'] == 'visitor'
		assert call.kwargs['properties']['$ai_trace_id'] == 'trace'
		assert call.kwargs['properties']['$ai_session_id'] == 'socket'
		assert call.kwargs['properties']['$session_id'] == 'replay'
	assert (
		generation_options_from_context()['posthog_distinct_id']
		is None
	)
	assert (
		'$session_id'
		not in generation_options_from_context()['posthog_properties']
	)


async def test_startup_uses_disabled_client_in_testing(monkeypatch):
	"""Use a disabled PostHog client in testing."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	monkeypatch.setenv('OPENAI_KEY', 'test')
	monkeypatch.setattr(config, '_openai_client', None)
	monkeypatch.setattr(
		ai_observability,
		'get_posthog_client',
		Mock(side_effect=AssertionError('must not use live client')),
	)
	config.start_openai_client()
	client = config.get_openai_client()
	try:
		assert isinstance(client, AsyncOpenAI)
		assert client._ph_client.disabled
		assert not client._ph_client.consumers
	finally:
		await config.stop_openai_client()


@pytest.mark.parametrize('cancelled', [False, True])
async def test_interrupted_stream_finalises_and_closes(
	wrapped, cancelled
):
	"""Early exit and cancellation still close the provider stream."""

	async def consume():
		with ai_observability_context(
			AIContext(ai_trace_id='interrupted')
		):
			async with aclosing(
				main.stream_agent_response(
					'system',
					[{'role': 'user', 'content': 'Hi'}],
				)
			) as events:
				await anext(events)
				if cancelled:
					raise asyncio.CancelledError()

	if cancelled:
		with pytest.raises(asyncio.CancelledError):
			await consume()
	else:
		await consume()
	wrapped.capture.assert_called_once()
	assert wrapped.responses[0].is_closed
	assert (
		wrapped.capture.call_args.kwargs['properties']['$ai_trace_id']
		== 'interrupted'
	)


@pytest.mark.parametrize('environment', ['development', 'production'])
async def test_startup_reuses_active_posthog(
	monkeypatch, environment
):
	"""Reuse the PostHog client started by the lifecycle."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', environment)
	monkeypatch.setenv('OPENAI_KEY', 'test')
	monkeypatch.setattr(config, '_openai_client', None)
	posthog = Posthog('disabled', disabled=True, sync_mode=True)
	monkeypatch.setattr(
		ai_observability, 'get_posthog_client', lambda: posthog
	)
	config.start_openai_client()
	try:
		assert config.get_openai_client()._ph_client is posthog
	finally:
		await config.stop_openai_client()
		posthog.shutdown()


async def test_concurrent_ai_contexts_are_isolated():
	"""Keep user and session metadata local to each task."""

	async def observe(user):
		with ai_observability_context(
			AIContext(user_id=user, ai_session_id=user)
		):
			await asyncio.sleep(0)
			return generation_options_from_context()

	first, second = await asyncio.gather(
		observe('one'), observe('two')
	)
	assert first['posthog_distinct_id'] == 'one'
	assert second['posthog_distinct_id'] == 'two'
	assert first['posthog_properties']['$ai_session_id'] == 'one'
	assert second['posthog_properties']['$ai_session_id'] == 'two'
	assert (
		generation_options_from_context()['posthog_distinct_id']
		is None
	)
