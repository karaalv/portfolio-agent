"""Check streamed socket events, terminal states and recursion."""

import asyncio
from collections.abc import AsyncIterator
from copy import deepcopy
from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from openai.types.responses import (
	Response,
	ResponseCompletedEvent,
	ResponseErrorEvent,
	ResponseFailedEvent,
	ResponseFunctionToolCall,
	ResponseIncompleteEvent,
	ResponseOutputItemAddedEvent,
	ResponseOutputItemDoneEvent,
	ResponseOutputMessage,
	ResponseStreamEvent,
	ResponseTextDeltaEvent,
)

from agent import main
from agent.observability import AgentTimer
from agent.streaming import delivery
from posthog_client import ai_observability


async def test_cancelled_turn_survives_failed_end_delivery(
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
	trace_capture: Mock,
) -> None:
	"""Do not replace cancellation with a secondary delivery error."""
	timer = AgentTimer()
	monkeypatch.setattr(
		main,
		'retrieve_agent_memory_param',
		AsyncMock(side_effect=asyncio.CancelledError()),
	)
	output.side_effect = [True, RuntimeError('closed transport')]
	with pytest.raises(asyncio.CancelledError):
		await main.agent_chat(
			'visitor', 'Hello', connection_id='socket', timer=timer
		)
	assert timer.outcome == 'cancelled'
	assert timer.records[-1].status == 'cancelled'
	trace_capture.assert_called_once()
	properties = trace_capture.call_args.kwargs['properties']
	assert properties['outcome'] == 'cancelled'
	assert properties['$ai_is_error'] is True
	assert properties['$ai_error'] == 'CancelledError'


@pytest.fixture
def trace_capture(monkeypatch: pytest.MonkeyPatch) -> Mock:
	"""Capture root trace events without starting telemetry."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')
	capture = Mock()
	monkeypatch.setattr(
		ai_observability,
		'get_posthog_client',
		lambda: SimpleNamespace(capture=capture),
	)
	return capture


@pytest.fixture
def output(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Capture queued output without requiring a socket."""
	mock = AsyncMock(return_value=True)
	monkeypatch.setattr(delivery, 'send_connection', mock)
	monkeypatch.setattr(
		main,
		'retrieve_agent_memory_param',
		AsyncMock(return_value=[]),
	)
	monkeypatch.setattr(
		main,
		'create_user_memory',
		AsyncMock(
			return_value=SimpleNamespace(
				payload={
					'role': 'user',
					'content': 'Hello',
				}
			)
		),
	)
	monkeypatch.setattr(
		main, 'create_response_item_memory', AsyncMock()
	)
	monkeypatch.setattr(
		main, 'create_response_input_memories', AsyncMock()
	)
	monkeypatch.setattr(
		main, 'run_function_calls', AsyncMock(return_value=[])
	)
	return mock


def _message() -> ResponseOutputMessage:
	"""Build a message item with SDK replay serialisation."""
	return ResponseOutputMessage(
		id='message',
		type='message',
		role='assistant',
		status='completed',
		content=[],
	)


def _completed(items: list) -> ResponseCompletedEvent:
	"""Supply only response fields the handler reads."""
	return ResponseCompletedEvent.model_construct(
		type='response.completed',
		sequence_number=4,
		response=Response.model_construct(output=items),
	)


def _install_stream(
	monkeypatch: pytest.MonkeyPatch,
	rounds: list[list[ResponseStreamEvent]],
) -> tuple[list, list[int]]:
	"""Capture model replay and verify streams close per round."""
	inputs: list = []
	closed: list[int] = []

	async def stream(
		**kwargs,
	) -> AsyncIterator[ResponseStreamEvent]:
		index = len(inputs)
		assert len(closed) == index
		inputs.append(deepcopy(kwargs['input']))
		try:
			for event in rounds[index]:
				yield event
		finally:
			closed.append(index)

	monkeypatch.setattr(main, 'stream_agent_response', stream)
	return inputs, closed


async def test_deltas_and_end_are_delivered_in_order(
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
	trace_capture: Mock,
) -> None:
	"""Send each text delta and one terminal event per turn."""
	item = _message()
	_, closed = _install_stream(
		monkeypatch,
		[
			[
				ResponseOutputItemAddedEvent.model_construct(
					type='response.output_item.added',
					item=item,
				),
				ResponseTextDeltaEvent.model_construct(
					type='response.output_text.delta',
					delta='Hello ',
				),
				ResponseTextDeltaEvent.model_construct(
					type='response.output_text.delta',
					delta='there',
				),
				ResponseOutputItemDoneEvent.model_construct(
					type='response.output_item.done',
					item=item,
				),
				_completed([item]),
			]
		],
	)
	await main.agent_chat('visitor', 'Hello', connection_id='socket')
	messages = [call.args[2] for call in output.await_args_list]
	assert [m.type for m in messages] == [
		'agent_start',
		'agent_delta',
		'agent_delta',
		'agent_end',
	]
	assert [m.payload.payload for m in messages[1:3]] == [
		'Hello ',
		'there',
	]
	assert [m.payload.sequence_number for m in messages[1:3]] == [
		0,
		1,
	]
	assert closed == [0]

	trace_capture.assert_called_once()
	properties = trace_capture.call_args.kwargs['properties']
	assert properties['$ai_input_state'] == [
		{'role': 'user', 'content': 'Hello'}
	]
	assert properties['$ai_output_state'] == [
		{'role': 'assistant', 'content': 'Hello there'}
	]
	assert properties['$ai_is_error'] is False


@pytest.mark.parametrize(
	'kind, expected',
	[
		('response.failed', 'error'),
		('error', 'error'),
		('response.incomplete', 'warning'),
		('interrupted', 'error'),
	],
)
async def test_terminal_failures_stop_without_persisting_output(
	kind: str,
	expected: str,
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
	trace_capture: Mock,
) -> None:
	"""End failed turns without continuing tools or saving output."""
	events: list[ResponseStreamEvent] = []
	if kind == 'response.failed':
		events.append(
			ResponseFailedEvent.model_construct(
				type=kind,
				response=Response.model_construct(error=None),
			)
		)
	elif kind == 'response.incomplete':
		events.append(
			ResponseIncompleteEvent.model_construct(
				type=kind,
				response=Response.model_construct(
					incomplete_details=None
				),
			)
		)
	elif kind == 'error':
		events.append(
			ResponseErrorEvent.model_construct(
				type=kind,
				message='Internal provider details',
			)
		)
	if kind != 'interrupted':
		events.append(_completed([_message()]))
	_, closed = _install_stream(monkeypatch, [events])
	timer = AgentTimer()
	summary = Mock()
	monkeypatch.setattr(main, 'log_turn_finished', summary)
	await main.agent_chat(
		'visitor',
		'Hello',
		connection_id='socket',
		timer=timer,
		posthog_session_id='session-1',
	)
	assert (
		timer.outcome
		== {
			'response.failed': 'failed',
			'error': 'failed',
			'response.incomplete': 'incomplete',
			'interrupted': 'interrupted',
		}[kind]
	)
	assert timer.records[-1].scope == 'interaction'
	summary.assert_called_once_with(
		timer, 'visitor', ANY, 'socket', 'session-1'
	)
	messages = [call.args[2] for call in output.await_args_list]
	assert [m.type for m in messages] == [
		'agent_start',
		expected,
		'agent_end',
	]
	assert 'Internal provider details' not in messages[1].payload
	assert closed == [0]
	assert (
		cast(AsyncMock, main.create_response_item_memory).await_count
		== 0
	)
	assert cast(AsyncMock, main.run_function_calls).await_count == 0

	trace_capture.assert_called_once()
	properties = trace_capture.call_args.kwargs['properties']
	assert properties['outcome'] == timer.outcome
	assert properties['$ai_is_error'] is True
	assert properties['$ai_output_state'] == []


async def test_tool_recursion_shares_connection_and_lifecycle(
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
	trace_capture: Mock,
) -> None:
	"""Replay tool results with one lifecycle across rounds."""
	tool = ResponseFunctionToolCall(
		type='function_call',
		call_id='call',
		name='fetch_context',
		arguments='{}',
		id='tool',
	)
	result = {
		'type': 'function_call_output',
		'call_id': 'call',
		'output': 'Grounded context',
	}
	cast(AsyncMock, main.run_function_calls).return_value = [result]
	inputs, closed = _install_stream(
		monkeypatch,
		[
			[_completed([tool])],
			[_completed([_message()])],
		],
	)
	timer = AgentTimer()
	await main.agent_chat(
		'visitor', 'Hello', connection_id='socket', timer=timer
	)
	assert [r.scope for r in timer.records] == [
		'openai',
		'openai',
		'interaction',
	]
	assert [r.name for r in timer.records[:2]] == [
		'Response round 1',
		'Response round 2',
	]
	assert (
		cast(AsyncMock, main.run_function_calls).call_args.kwargs[
			'timer'
		]
		is timer
	)
	messages = [call.args[2] for call in output.await_args_list]
	assert [m.type for m in messages] == [
		'agent_start',
		'tool_message',
		'agent_end',
	]
	assert messages[1].payload == {'fetch_context'}
	assert inputs[1][-1] == result
	assert closed == [0, 1]
	assert all(
		call.args[:2] == ('visitor', 'socket')
		for call in output.await_args_list
	)

	trace_capture.assert_called_once()


async def test_direct_agent_calls_do_not_require_registry(
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Preserve terminal and integration callers without a socket."""
	_install_stream(monkeypatch, [[_completed([_message()])]])
	await main.agent_chat('visitor', 'Hello')
	output.assert_not_awaited()


async def test_model_timer_excludes_output_persistence(
	output: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Keep database writes in turn time, outside model time."""
	from agent.observability import timing

	clock = [0.0]
	monkeypatch.setattr(timing, 'perf_counter', lambda: clock[0])

	async def stream(**kwargs) -> AsyncIterator[ResponseStreamEvent]:
		"""Spend two seconds producing the terminal response."""
		clock[0] += 2.0
		yield _completed([_message()])

	async def persist(**kwargs) -> None:
		"""Spend ten seconds writing the completed output."""
		clock[0] += 10.0

	monkeypatch.setattr(main, 'stream_agent_response', stream)
	monkeypatch.setattr(main, 'create_response_item_memory', persist)
	timer = AgentTimer()
	await main.agent_chat('visitor', 'Hello', timer=timer)
	assert [(r.scope, r.duration_seconds) for r in timer.records] == [
		('openai', 2.0),
		('interaction', 12.0),
	]
