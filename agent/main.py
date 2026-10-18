"""
Coordinate portfolio conversations, retrieval tools, and memory.
"""

import asyncio
import sys
from collections.abc import Callable
from contextlib import aclosing

from openai.types.responses import (
	Response,
	ResponseInputParam,
	ResponseStreamEvent,
)
from opentelemetry.trace import Span, StatusCode

from agent.config.agent import AGENT_TOOL_RECURSION_LIMIT
from agent.input_items import response_item_to_input_item
from agent.logging.events import log_stream_outcome, log_turn_finished
from agent.logging.terminal import log_agent_history
from agent.memory.creation import (
	create_response_input_memories,
	create_response_item_memory,
	create_user_memory,
)
from agent.memory.retrieval import (
	retrieve_agent_memory_param,
)
from agent.observability import AgentTimer
from agent.prompts.agent import AGENT_SYSTEM_PROMPT
from agent.prompts.behaviour import AGENT_BEHAVIOUR_PROMPT
from agent.streaming.delivery import send_agent_ws_response
from agent.streaming.stream_manager import StreamManager
from agent.tools.dispatch import run_function_calls
from agent.tools.tool_definitions import AGENT_TOOL_DEFINITIONS
from agent.validation import raise_agent_recursion_limit
from api.websocket.helpers.responses import (
	create_ws_agent_delta_response,
	create_ws_agent_end_response,
	create_ws_agent_start_response,
	create_ws_error_response,
	create_ws_tool_message_response,
	create_ws_warning_response,
)
from openai_client.main import stream_agent_response
from posthog_client.ai_observability import (
	AIContext,
	ai_observability_context,
)
from posthog_client.tracing import start_span
from schemas.agent.streaming.stream_manager import (
	EventStreamState,
)
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, rich_print


async def agent_chat(
	user_id: str,
	user_input: str,
	history: ResponseInputParam | None = None,
	verbosity_level: int = 0,
	connection_id: str | None = None,
	timer: AgentTimer | None = None,
	posthog_session_id: str | None = None,
	ai_session_id: str | None = None,
) -> None:
	"""Answer one turn and persist its input and final response.

	Allow up to three rounds of context retrieval. Load history
	before storing input so it appears only once. An optional
	connection ID enables socket delivery for the whole turn.
	Pass a fresh timer to inspect timings across all rounds.
	"""

	timer = timer if timer is not None else AgentTimer()
	stream_manager = StreamManager(
		user_id=user_id, verbosity_level=verbosity_level
	)
	with start_span(
		'agent.turn',
		user_id,
		posthog_session_id,
		attributes={
			'turn_id': stream_manager.get_turn_id(),
			'connection_id': connection_id,
		},
	) as turn_span:
		ai_trace_id = _set_ai_tracing_attributes(
			turn_span, ai_session_id
		)
		with ai_observability_context(
			AIContext(
				user_id=user_id,
				session_id=posthog_session_id,
				ai_trace_id=ai_trace_id,
				ai_session_id=ai_session_id,
			)
		):
			try:
				with timer.measure(
					'interaction', 'Agent turn'
				) as interaction:
					try:
						await send_agent_ws_response(
							user_id,
							connection_id,
							create_ws_agent_start_response(
								'Agent turn started.'
							),
						)
						try:
							with start_span(
								'agent.memory.retrieve',
								user_id,
								posthog_session_id,
							) as memory_span:
								history = (
									await retrieve_agent_memory_param(
										user_id=user_id
									)
								)
								memory_span.set_attribute(
									'history_count', len(history)
								)
							current_memory = await create_user_memory(
								user_id=user_id,
								turn_id=stream_manager.get_turn_id(),
								sequence=stream_manager.increment_turn_sequence_counter(),
								content=user_input,
							)
							history.append(current_memory.payload)
							if verbosity_level > 1:
								log_agent_history(history)
							await _agent_response_handler(
								stream_manager=stream_manager,
								history=history,
								verbosity_level=verbosity_level,
								connection_id=connection_id,
								timer=timer,
								posthog_session_id=posthog_session_id,
							)
						finally:
							pending = sys.exception()
							try:
								await send_agent_ws_response(
									user_id,
									connection_id,
									create_ws_agent_end_response(
										'Agent turn ended.'
									),
								)
							except Exception as cleanup_error:
								if pending is None:
									raise
								pending.add_note(
									'Agent-end delivery also failed: '
									f'{type(cleanup_error).__name__}'
								)
					except asyncio.CancelledError:
						timer.mark_outcome('cancelled')
						raise
					except Exception:
						timer.mark_outcome('failed')
						raise
					finally:
						interaction.finish(timer.outcome)
			finally:
				turn_span.set_attribute('outcome', timer.outcome)
				if timer.outcome in {
					'failed',
					'interrupted',
					'incomplete',
					'degraded',
				}:
					turn_span.set_status(StatusCode.ERROR)
				log_turn_finished(
					timer,
					user_id,
					stream_manager.get_turn_id(),
					connection_id,
					posthog_session_id,
				)


# --- Helper Functions ---


async def _agent_response_handler(
	stream_manager: StreamManager,
	history: ResponseInputParam,
	verbosity_level: int,
	recursion_depth: int = 0,
	connection_id: str | None = None,
	timer: AgentTimer | None = None,
	posthog_session_id: str | None = None,
) -> None:
	"""
	Handles the agent response lifecycle,
	processing events, and managing the state
	of the conversation and function calls.
	"""
	timer = timer if timer is not None else AgentTimer()
	if recursion_depth > AGENT_TOOL_RECURSION_LIMIT:
		raise_agent_recursion_limit()

	client_stream = stream_agent_response(
		system_prompt=_get_agent_system_prompt(),
		input=history,
		tools=AGENT_TOOL_DEFINITIONS,
	)

	completed = False
	completed_response: Response | None = None
	user_id = stream_manager.get_user_id()
	with (
		start_span(
			'agent.openai.stream',
			user_id,
			posthog_session_id,
			attributes={'round': recursion_depth + 1},
		) as response_span,
		timer.measure(
			'openai', f'Response round {recursion_depth + 1}'
		) as response_timing,
	):
		async with aclosing(client_stream) as events:
			async for event in events:
				_log_event_state(
					event,
					response_span,
					timer,
					response_timing.finish,
				)
				if verbosity_level > 1:
					rich_print(
						f'Received event: {event}',
						style=LogStyle.DEFAULT,
					)

				if event.type == 'response.output_item.added':
					# Resolve event type
					if event.item.type == 'function_call':
						stream_manager.set_function_call_state()
					elif event.item.type == 'message':
						stream_manager.set_message_state()
				elif event.type == 'response.output_text.delta':
					# Handle text delta
					if (
						stream_manager.get_event_stream_state()
						== EventStreamState.MESSAGE
					):
						response = stream_manager.add_delta(
							event.delta
						)
						await send_agent_ws_response(
							user_id,
							connection_id,
							create_ws_agent_delta_response(response),
						)
				elif event.type == 'response.output_item.done':
					if event.item.type == 'message':
						stream_manager.set_idle_state()
				elif event.type == 'response.completed':
					completed = True
					completed_response = event.response
					break
				elif event.type in {
					'response.failed',
					'response.incomplete',
					'error',
				}:
					message = {
						'response.failed': (
							'Could not generate a response. '
							'Please try again.'
						),
						'response.incomplete': (
							'This response is incomplete. '
							'Please try again.'
						),
						'error': (
							'The response was interrupted. '
							'Please try again.'
						),
					}[event.type]
					await _record_failed_stream(
						'incomplete'
						if event.type == 'response.incomplete'
						else 'failed',
						message,
						stream_manager,
						timer,
						recursion_depth + 1,
						connection_id,
						posthog_session_id,
						event,
					)
					return
		response_timing.finish('interrupted')
		if not completed:
			response_span.set_attribute('outcome', 'interrupted')
			response_span.set_status(StatusCode.ERROR)

	# Stream closed
	if not completed:
		await _log_stream_as_interrupted(
			stream_manager,
			timer,
			recursion_depth + 1,
			connection_id,
			posthog_session_id,
		)
		return

	if completed_response is not None:
		await _capture_completed_response(
			completed_response, stream_manager, history
		)

	# Run function calls from manager and
	# return results.
	if stream_manager.has_function_calls():
		calls = stream_manager.get_function_calls().values()
		await send_agent_ws_response(
			user_id,
			connection_id,
			create_ws_tool_message_response(
				{call.tool_name for call in calls}
			),
		)
		results = await run_function_calls(
			user_id=stream_manager.get_user_id(),
			function_calls=stream_manager.get_function_calls(),
			verbose=verbosity_level > 0,
			timer=timer,
			posthog_session_id=posthog_session_id,
			connection_id=connection_id,
		)
		await create_response_input_memories(
			stream_manager=stream_manager,
			payloads=results,
		)
		stream_manager.clear_function_calls()
		# Recursive case: Another round
		# of agent response
		return await _agent_response_handler(
			stream_manager=stream_manager,
			history=history + results,
			verbosity_level=verbosity_level,
			recursion_depth=recursion_depth + 1,
			connection_id=connection_id,
			timer=timer,
			posthog_session_id=posthog_session_id,
		)

	# Base case: Successfully reached the
	# terminal answer
	return None


async def _record_failed_stream(
	outcome: str,
	message: str,
	stream_manager: StreamManager,
	timer: AgentTimer,
	round_index: int,
	connection_id: str | None,
	posthog_session_id: str | None,
	event: ResponseStreamEvent | None = None,
) -> None:
	"""Record a terminal failure and send its socket response."""
	timer.mark_outcome(outcome)
	user_id = stream_manager.get_user_id()
	log_stream_outcome(
		event.type if event is not None else 'interrupted',
		user_id,
		stream_manager.get_turn_id(),
		round_index,
		connection_id,
		posthog_session_id,
		event,
	)
	response = (
		create_ws_warning_response(message)
		if outcome == 'incomplete'
		else create_ws_error_response(message)
	)
	await send_agent_ws_response(user_id, connection_id, response)


async def _log_stream_as_interrupted(
	stream_manager: StreamManager,
	timer: AgentTimer,
	round_index: int,
	connection_id: str | None,
	posthog_session_id: str | None,
) -> None:
	"""Report a stream closed without a terminal provider event."""
	await _record_failed_stream(
		'interrupted',
		'The response was interrupted. Please try again.',
		stream_manager,
		timer,
		round_index,
		connection_id,
		posthog_session_id,
	)


async def _capture_completed_response(
	completed_response: Response,
	stream_manager: StreamManager,
	history: ResponseInputParam,
) -> None:
	"""Persist response items and collect their pending tool calls."""
	for item in completed_response.output:
		# Append the response item to the
		# conversation history
		payload = response_item_to_input_item(item)
		await create_response_item_memory(
			stream_manager=stream_manager,
			payload=payload,
		)
		history.append(payload)

		if item.type == 'function_call':
			stream_manager.add_function_call(
				call_id=item.call_id,
				tool_name=item.name,
				tool_args=item.arguments,
			)


def _set_ai_tracing_attributes(
	span: Span, ai_session_id: str | None
) -> str:
	"""Set AI tracing attributes and return the turn trace ID."""
	span_context = span.get_span_context()
	ai_trace_id = (
		f'{span_context.trace_id:032x}'
		if span_context.is_valid
		else generate_uuid_str()
	)
	span.set_attribute('ai_trace_id', ai_trace_id)
	if ai_session_id is not None:
		span.set_attribute('ai_session_id', ai_session_id)
	return ai_trace_id


def _log_event_state(
	event: ResponseStreamEvent,
	span: Span,
	timer: AgentTimer,
	finish_timing: Callable[[str], None],
) -> None:
	"""Update span metadata and time terminal response events."""
	response = getattr(event, 'response', None)
	model = getattr(response, 'model', None)
	if model is not None:
		timer.model = model
		span.set_attribute('model', model)
	reasoning = getattr(
		getattr(response, 'reasoning', None), 'effort', None
	)
	if reasoning is not None:
		span.set_attribute('reasoning', reasoning)
	if event.type in {
		'response.completed',
		'response.failed',
		'response.incomplete',
		'error',
	}:
		finish_timing(event.type)
		span.set_attribute('outcome', event.type)
		if event.type != 'response.completed':
			span.set_status(StatusCode.ERROR)


def _get_agent_system_prompt() -> str:
	return AGENT_SYSTEM_PROMPT + '\n\n' + AGENT_BEHAVIOUR_PROMPT
