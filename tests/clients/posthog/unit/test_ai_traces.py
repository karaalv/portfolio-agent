"""Check explicit AI traces without sending telemetry."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from posthog_client import ai_observability as module
from posthog_client.ai_observability import (
	AIContext,
	ai_observability_context,
	capture_agent_trace,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch) -> Mock:
	"""Capture events locally using an active environment."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')
	mock = Mock()
	monkeypatch.setattr(
		module,
		'get_posthog_client',
		lambda: SimpleNamespace(capture=mock),
	)
	return mock


def _capture(outcome: str = 'completed', **kwargs) -> None:
	"""Supply fixed turn data under explicit attribution."""
	with ai_observability_context(
		AIContext('visitor', 'replay', 'trace', 'socket')
	):
		capture_agent_trace(
			user_input='What does Alvin do?',
			output_text='He builds products.',
			duration_seconds=4.5,
			started_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
			outcome=outcome,
			turn_id='turn',
			**kwargs,
		)


def test_trace_captures_conversation_and_attribution(capture):
	"""Keep root I/O, latency and session IDs on one trace event."""
	_capture()
	capture.assert_called_once()
	assert capture.call_args.args == ('$ai_trace',)
	kwargs = capture.call_args.kwargs
	assert kwargs['distinct_id'] == 'visitor'
	assert kwargs['timestamp'] == datetime(
		2026, 10, 20, tzinfo=timezone.utc
	)
	properties = kwargs['properties']
	assert properties['$ai_trace_id'] == 'trace'
	assert properties['$ai_session_id'] == 'socket'
	assert properties['$session_id'] == 'replay'
	assert properties['environment'] == 'development'
	assert properties['turn_id'] == 'turn'
	assert properties['$ai_span_name'] == 'Portfolio chat'
	assert properties['$ai_latency'] == 4.5
	assert properties['$ai_input_state'] == [
		{'role': 'user', 'content': 'What does Alvin do?'}
	]
	assert properties['$ai_output_state'] == [
		{'role': 'assistant', 'content': 'He builds products.'}
	]
	assert properties['$ai_is_error'] is False
	assert '$ai_error' not in properties


@pytest.mark.parametrize(
	'outcome',
	['failed', 'cancelled', 'incomplete', 'interrupted', 'degraded'],
)
def test_unsuccessful_trace_records_outcome(capture, outcome):
	"""Record non-exception failures and partial response text."""
	_capture(outcome)
	properties = capture.call_args.kwargs['properties']
	assert properties['$ai_is_error'] is True
	assert properties['$ai_error'] == outcome
	assert properties['outcome'] == outcome
	assert properties['$ai_output_state'][0]['content']


def test_exception_trace_records_error_class(capture):
	"""Identify the failure without copying exception details."""
	_capture('failed', error=ValueError('internal details'))
	properties = capture.call_args.kwargs['properties']
	assert properties['$ai_error'] == 'ValueError'


def test_capture_failure_does_not_escape(capture, monkeypatch):
	"""Telemetry failures must not replace the agent outcome."""
	capture.side_effect = RuntimeError('unavailable')
	log = Mock()
	monkeypatch.setattr(module, 'log_error', log)
	_capture()
	log.assert_called_once()
	assert log.call_args.args[0] == 'telemetry_capture_failed'


def test_testing_does_not_capture(capture, monkeypatch):
	"""Keep test traffic out of the live PostHog project."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	_capture()
	capture.assert_not_called()


def test_missing_trace_context_does_not_capture(capture):
	"""Do not emit root events without a matching trace ID."""
	with ai_observability_context(AIContext(user_id='visitor')):
		capture_agent_trace(
			user_input='Hello',
			output_text='',
			duration_seconds=0,
			started_at=datetime.now(timezone.utc),
			outcome='failed',
			turn_id='turn',
		)
	capture.assert_not_called()
