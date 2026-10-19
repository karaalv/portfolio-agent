"""Verify span boundaries, context and identity isolation."""

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
	InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode, get_current_span

from agent import main
from agent.tools import dispatch
from api.maintenance import user_data_pruner
from api.routes import agent_memory, users
from exceptions.authorisation import JwtValidationException
from posthog_client import _logging
from posthog_client.ai_observability import (
	generation_options_from_context,
)
from posthog_client.tracing import start_span
from schemas.api.http.users import ClaimCookieRequest
from security.observers import block_observer, usage_observer
from security.ratelimit.ratelimit_store import RateLimitStore
from shared.time import get_utc_datetime_now

pytestmark = pytest.mark.unit


@pytest.fixture
def spans(monkeypatch) -> Iterator[InMemorySpanExporter]:
	"""Use real OTel context with an in-memory exporter."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')
	provider = TracerProvider(shutdown_on_exit=False)
	exporter = InMemorySpanExporter()
	provider.add_span_processor(SimpleSpanProcessor(exporter))
	monkeypatch.setattr(_logging, '_tracer_provider', provider)
	try:
		yield exporter
	finally:
		provider.shutdown()


async def test_parallel_spans_keep_identity_and_parentage(spans):
	"""Keep parent context and isolate concurrent identities."""

	async def child(user):
		with start_span('child', user, None):
			await asyncio.sleep(0)
			assert get_current_span().is_recording()

	with start_span('root', None, None) as root:
		await asyncio.gather(child('one'), child('two'))
		assert get_current_span() is root
	children = spans.get_finished_spans()[:2]
	assert {s.attributes['posthogDistinctId'] for s in children} == {
		'one',
		'two',
	}
	assert all(
		s.parent.span_id == root.get_span_context().span_id
		for s in children
	)
	assert all('sessionId' not in s.attributes for s in children)
	assert not spans.get_finished_spans()[-1].attributes
	assert not get_current_span().is_recording()


def test_failure_records_error_and_propagates_original(spans):
	"""Tracing must not swallow the application failure."""
	error = ValueError('failed')
	with pytest.raises(ValueError) as caught, start_span('failure'):
		raise error
	assert caught.value is error
	assert (
		spans.get_finished_spans()[0].status.status_code
		== StatusCode.ERROR
	)


def test_testing_does_not_record_even_with_provider(
	spans, monkeypatch
):
	"""Suppress test telemetry independently of startup."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	with start_span('test') as span:
		assert not span.is_recording()
	assert not spans.get_finished_spans()


async def test_agent_turn_spans_include_stream_and_tools(
	spans, monkeypatch
):
	"""Model rounds and parallel tools are siblings under one turn."""
	monkeypatch.setattr(main, 'send_agent_ws_response', AsyncMock())
	monkeypatch.setattr(
		main,
		'retrieve_agent_memory_param',
		AsyncMock(return_value=[]),
	)
	monkeypatch.setattr(
		main,
		'create_user_memory',
		AsyncMock(return_value=SimpleNamespace(payload={})),
	)
	monkeypatch.setattr(
		main, 'create_response_item_memory', AsyncMock()
	)
	monkeypatch.setattr(
		main, 'create_response_input_memories', AsyncMock()
	)
	rounds = 0
	attribution = []

	async def stream(**kwargs):
		nonlocal rounds
		assert (
			not {
				'user_id',
				'posthog_session_id',
				'ai_trace_id',
				'ai_session_id',
			}
			& kwargs.keys()
		)
		attribution.append(generation_options_from_context())
		rounds += 1
		output = []
		if rounds == 1:
			output = [
				SimpleNamespace(
					type='function_call',
					call_id='call',
					name='fetch_context',
					arguments='{}',
				)
			]
		yield SimpleNamespace(
			type='response.completed',
			response=SimpleNamespace(
				model='model',
				reasoning=SimpleNamespace(effort='medium'),
				output=output,
			),
		)

	monkeypatch.setattr(main, 'stream_agent_response', stream)
	monkeypatch.setattr(
		main, 'response_item_to_input_item', lambda item: {}
	)
	monkeypatch.setattr(
		dispatch, 'fetch_context', AsyncMock(return_value='context')
	)
	await main.agent_chat(
		'visitor',
		'Hello',
		posthog_session_id='session',
		ai_session_id='socket',
	)
	recorded = spans.get_finished_spans()
	turn = recorded[-1]
	assert turn.name == 'agent.turn'
	assert turn.parent is None
	assert turn.attributes['outcome'] == 'completed'
	assert [s.name for s in recorded[:-1]] == [
		'agent.memory.retrieve',
		'agent.openai.stream',
		'agent.tool',
		'agent.openai.stream',
	]
	assert all(
		s.parent.span_id == turn.context.span_id
		for s in recorded[:-1]
	)
	assert all(
		s.attributes['sessionId'] == 'session' for s in recorded
	)
	assert recorded[0].attributes['history_count'] == 0
	assert recorded[1].attributes['model'] == 'model'
	assert recorded[1].attributes['reasoning'] == 'medium'
	assert recorded[2].attributes['tool_name'] == 'fetch_context'
	assert recorded[2].attributes['tool_args'] == '{}'
	for request in attribution:
		assert request['posthog_distinct_id'] == 'visitor'
		assert (
			request['posthog_properties']['$session_id'] == 'session'
		)
		assert (
			request['posthog_trace_id']
			== f'{turn.context.trace_id:032x}'
		)
		assert (
			request['posthog_properties']['$ai_session_id']
			== 'socket'
		)
	await main.agent_chat('visitor', 'Again')
	assert (
		attribution[-1]['posthog_trace_id']
		!= attribution[0]['posthog_trace_id']
	)
	assert (
		spans.get_finished_spans()[-1].context.trace_id
		!= turn.context.trace_id
	)


def request():
	"""Include forged browser identity to check server attribution."""
	return Request(
		{
			'type': 'http',
			'headers': [(b'x-posthog-distinct-id', b'forged')],
			'state': {
				'request_id': 'request',
				'posthog_session_id': 'session',
			},
		}
	)


async def test_memory_endpoints_have_standalone_spans(
	spans, monkeypatch
):
	"""Capture request context without adding database spans."""
	monkeypatch.setattr(
		agent_memory,
		'retrieve_agent_chat_page',
		AsyncMock(return_value=[]),
	)
	monkeypatch.setattr(
		agent_memory, 'delete_agent_memory', AsyncMock()
	)
	await agent_memory.fetch_chat_page(request(), 'visitor')
	await agent_memory.delete_memory(request(), 'visitor')
	for span in spans.get_finished_spans():
		assert span.parent is None
		assert span.attributes['posthogDistinctId'] == 'visitor'
		assert span.attributes['sessionId'] == 'session'
		assert span.attributes['request_id'] == 'request'
	assert len(spans.get_finished_spans()) == 2


@pytest.mark.parametrize('valid', [True, False])
async def test_cookie_span_never_contains_token(
	spans, monkeypatch, valid
):
	"""Identify only validated claims and exclude token content."""
	token = 'private-token'

	def validate(value):
		if not valid:
			raise JwtValidationException('Invalid token.')
		return {
			'sub': 'visitor',
			'exp': (
				get_utc_datetime_now() + timedelta(hours=1)
			).timestamp(),
		}

	monkeypatch.setattr(users, 'validate_token', validate)
	monkeypatch.setattr(
		users, 'does_user_exist', AsyncMock(return_value=True)
	)
	monkeypatch.setattr(users, 'check_entity_block', AsyncMock())
	monkeypatch.setattr(users, 'get_cookie_domain', lambda: None)
	if valid:
		await users.claim_cookie(
			request(), ClaimCookieRequest(claim_token=token)
		)
	else:
		with pytest.raises(HTTPException):
			await users.claim_cookie(
				request(), ClaimCookieRequest(claim_token=token)
			)
	span = spans.get_finished_spans()[0]
	assert ('posthogDistinctId' in span.attributes) is valid
	assert token not in str(span.attributes)
	assert token not in str(span.events)


@pytest.mark.parametrize(
	'job', ['usage', 'blocks', 'users', 'rate_limits']
)
async def test_maintenance_runs_have_no_visitor_identity(
	spans,
	monkeypatch,
	job,
):
	"""Trace maintenance passes without visitor attribution."""
	if job == 'usage':
		monkeypatch.setattr(
			usage_observer,
			'reset_daily_usage',
			AsyncMock(return_value=2),
		)
		monkeypatch.setattr(
			usage_observer,
			'prune_inactive_usage',
			AsyncMock(return_value=1),
		)
		await usage_observer.UsageObserver().run_once()
	elif job == 'blocks':
		monkeypatch.setattr(
			block_observer,
			'prune_expired_blocks',
			AsyncMock(return_value=1),
		)
		await block_observer.BlockObserver().run_once()
	elif job == 'users':
		monkeypatch.setattr(
			user_data_pruner,
			'get_collection',
			lambda collection: None,
		)
		pruner = user_data_pruner.UserDataPruner()
		monkeypatch.setattr(
			pruner,
			'_get_inactive_users',
			AsyncMock(return_value=set()),
		)
		await pruner.prune_once()
	else:
		store = RateLimitStore()
		try:
			await store.prune_once()
		finally:
			await store.stop()
	recorded = spans.get_finished_spans()
	assert len(recorded) == 1
	assert recorded[0].name.startswith('maintenance.')
	assert recorded[0].parent is None
	assert 'posthogDistinctId' not in recorded[0].attributes
	assert 'sessionId' not in recorded[0].attributes


async def test_failed_maintenance_span_is_error(spans, monkeypatch):
	"""Record failed maintenance before the scheduler retries."""
	monkeypatch.setattr(
		block_observer,
		'prune_expired_blocks',
		AsyncMock(side_effect=RuntimeError('database unavailable')),
	)
	with pytest.raises(RuntimeError):
		await block_observer.BlockObserver().run_once()
	assert (
		spans.get_finished_spans()[0].status.status_code
		== StatusCode.ERROR
	)
