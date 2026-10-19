"""Run tools concurrently and return results in call order."""

import asyncio

from openai.types.responses import ResponseInputParam
from opentelemetry.trace import StatusCode, get_current_span
from pydantic import ValidationError

from agent.input_items import create_function_output_item
from agent.logging.tools import (
	capture_tool_failure,
	log_tool_rejected,
)
from agent.observability import AgentTimer
from agent.prompts.tools import (
	format_failed_tool_response,
	format_tool_exception_response,
)
from agent.tools.context import fetch_context
from posthog_client.tracing import start_span
from schemas.agent.streaming.stream_manager import (
	StreamManagerFunctionCall,
)
from schemas.agent.tools import AgentToolName
from shared.logging import LogStyle, rich_print


async def run_function_calls(
	user_id: str,
	function_calls: dict[str, StreamManagerFunctionCall],
	verbose: bool = False,
	timer: AgentTimer | None = None,
	connection_id: str | None = None,
	posthog_session_id: str | None = None,
) -> ResponseInputParam:
	"""Run calls concurrently; return dictionary insertion order.

	Each result retains its originating call ID. Report tool
	failures as outputs so the model can revise its next call.
	"""
	calls = list(function_calls.values())
	async with asyncio.TaskGroup() as group:
		tasks: list[asyncio.Task[str]] = []
		for call in calls:
			if verbose:
				rich_print(
					f'Running {call.tool_name} ({call.call_id}).',
					style=LogStyle.INFO,
				)
			tasks.append(
				group.create_task(
					_run_tool_call(
						user_id,
						call,
						verbose,
						timer,
						connection_id,
						posthog_session_id,
					)
				)
			)

	return [
		create_function_output_item(call.call_id, task.result())
		for call, task in zip(calls, tasks, strict=True)
	]


async def _run_tool_call(
	user_id: str,
	call: StreamManagerFunctionCall,
	verbose: bool,
	timer: AgentTimer | None,
	connection_id: str | None,
	posthog_session_id: str | None,
) -> str:
	"""Time each tool independently, preserving call identity."""
	with start_span(
		'agent.tool',
		user_id,
		posthog_session_id,
		attributes={
			'tool_name': call.tool_name,
			'tool_args': call.tool_args,
		},
	):
		if timer is None:
			return await _dispatch_tool_call(
				user_id,
				call.tool_name,
				call.tool_args,
				verbose,
				connection_id,
				posthog_session_id=posthog_session_id,
				call_id=call.call_id,
			)
		with timer.measure(
			'tool', f'{call.tool_name} ({call.call_id})'
		):
			return await _dispatch_tool_call(
				user_id,
				call.tool_name,
				call.tool_args,
				verbose,
				connection_id,
				posthog_session_id=posthog_session_id,
				call_id=call.call_id,
				timer=timer,
			)


async def _dispatch_tool_call(
	user_id: str,
	tool_name: str | None,
	tool_args: str,
	verbose: bool = False,
	connection_id: str | None = None,
	posthog_session_id: str | None = None,
	call_id: str | None = None,
	timer: AgentTimer | None = None,
) -> str:
	"""Dispatch a tool and report recoverable failures."""
	try:
		match tool_name:
			case AgentToolName.FETCH_CONTEXT:
				result = await fetch_context(
					user_id=user_id,
					tool_args=tool_args,
					verbose=verbose,
					connection_id=connection_id,
				)
			case _:
				get_current_span().set_status(StatusCode.ERROR)
				if timer is not None:
					timer.mark_outcome('degraded')
				log_tool_rejected(
					user_id,
					tool_name,
					call_id,
					connection_id,
					posthog_session_id,
					'unknown_tool',
				)
				message = f'Unknown tool: {tool_name!r}.'
				if verbose:
					rich_print(message, style=LogStyle.WARNING)
				return format_failed_tool_response(message)
	except ValidationError as error:
		get_current_span().set_status(StatusCode.ERROR)
		if timer is not None:
			timer.mark_outcome('degraded')
		log_tool_rejected(
			user_id,
			tool_name,
			call_id,
			connection_id,
			posthog_session_id,
			'invalid_arguments',
		)
		details = error.errors(include_input=False, include_url=False)
		message = f'Invalid arguments for {tool_name}: {details}'
		if verbose:
			rich_print(message, style=LogStyle.WARNING)
		return format_failed_tool_response(message)
	except Exception as error:
		get_current_span().set_status(StatusCode.ERROR)
		if timer is not None:
			timer.mark_outcome('degraded')
		capture_tool_failure(
			error,
			user_id,
			tool_name,
			call_id,
			connection_id,
			posthog_session_id,
		)
		message = (
			f'Unexpected error for {tool_name}: '
			f'{type(error).__name__}: {error}'
		)
		if verbose:
			rich_print(
				message,
				style=LogStyle.ERROR,
			)
		return format_tool_exception_response(
			tool_name=str(tool_name),
			message=message,
		)

	if verbose:
		rich_print(
			f'Tool {tool_name} completed: {len(result)} characters.',
			style=LogStyle.SUCCESS,
		)
	return result
