"""Check ordered tool outputs and recoverable dispatch errors."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from agent.tools import dispatch
from schemas.agent.streaming.stream_manager import (
	StreamManagerFunctionCall,
)

pytestmark = pytest.mark.unit


async def test_parallel_calls_return_original_order(monkeypatch):
	"""
	Finish the second call first but retain originating IDs.
	"""
	both_started = asyncio.Event()
	second_finished = asyncio.Event()
	started = []

	async def run(user_id, tool_name, tool_args, verbose):
		"""
		Coordinate reverse completion without timing sleeps.
		"""
		started.append(tool_args)
		if len(started) == 2:
			both_started.set()
		await asyncio.wait_for(both_started.wait(), 2)
		if tool_args == 'first':
			await asyncio.wait_for(second_finished.wait(), 2)
		else:
			second_finished.set()
		assert user_id == 'visitor'
		return f'context-{tool_args}'

	monkeypatch.setattr(dispatch, '_dispatch_tool_call', run)
	calls = {
		name: StreamManagerFunctionCall(
			call_id=f'call-{name}',
			tool_name='fetch_context',
			tool_args=name,
		)
		for name in ('first', 'second')
	}
	results = await dispatch.run_function_calls('visitor', calls)
	assert results == [
		{
			'type': 'function_call_output',
			'call_id': 'call-first',
			'output': 'context-first',
		},
		{
			'type': 'function_call_output',
			'call_id': 'call-second',
			'output': 'context-second',
		},
	]
	assert await dispatch.run_function_calls('visitor', {}) == []


async def test_valid_dispatch_preserves_json_arguments(
	monkeypatch,
):
	"""Pass raw arguments and return unwrapped context text."""
	tool = AsyncMock(return_value='Grounded context')
	monkeypatch.setattr(dispatch, 'fetch_context', tool)
	arguments = '{"user_input":"education"}'
	assert (
		await dispatch._dispatch_tool_call(
			'visitor', 'fetch_context', arguments
		)
		== 'Grounded context'
	)
	tool.assert_awaited_once_with(
		user_id='visitor', tool_args=arguments, verbose=False
	)


@pytest.mark.parametrize('name', ['unknown', None])
async def test_unknown_tool_returns_error(name, monkeypatch):
	"""Report invalid names without invoking a real tool."""
	tool = AsyncMock()
	monkeypatch.setattr(dispatch, 'fetch_context', tool)
	result = await dispatch._dispatch_tool_call(
		'visitor', name, '{}'
	)
	assert 'tool execution failed' in result
	assert 'Unknown tool' in result
	tool.assert_not_awaited()


@pytest.mark.parametrize(
	'arguments',
	[
		'not json',
		'{}',
		'{"user_input":12}',
		'{"user_input":"education","unexpected":true}',
	],
)
async def test_invalid_arguments_return_error(arguments):
	"""Use the real argument validator before any RAG call."""
	result = await dispatch._dispatch_tool_call(
		'visitor', 'fetch_context', arguments
	)
	assert 'tool execution failed' in result
	assert 'Invalid arguments' in result


async def test_backend_failure_is_packaged(monkeypatch):
	"""Keep backend exceptions replayable as tool output text."""
	tool = AsyncMock(side_effect=RuntimeError('Unavailable'))
	monkeypatch.setattr(dispatch, 'fetch_context', tool)
	result = await dispatch._dispatch_tool_call(
		'visitor', 'fetch_context', '{}'
	)
	assert 'encountered an exception' in result
	assert 'RuntimeError: Unavailable' in result
