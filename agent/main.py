"""
Coordinate portfolio conversations, retrieval tools, and memory.
"""

import asyncio
import sys
from contextlib import aclosing

from openai.types.responses import ResponseInputParam

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
from schemas.agent.streaming.stream_manager import (
	EventStreamState,
)
from shared.logging import LogStyle, rich_print


async def agent_chat(
	user_id: str,
	user_input: str,
	history: ResponseInputParam | None = None,
	verbosity_level: int = 0,
	connection_id: str | None = None,
	timer: AgentTimer | None = None,
	posthog_session_id: str | None = None,
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
					history = await retrieve_agent_memory_param(
						user_id=user_id
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
	user_id = stream_manager.get_user_id()
	with timer.measure(
		'openai', f'Response round {recursion_depth + 1}'
	) as response_timing:
		async with aclosing(client_stream) as events:
			async for event in events:
				model = getattr(
					getattr(event, 'response', None), 'model', None
				)
				if model is not None:
					timer.model = model
				if event.type in {
					'response.completed',
					'response.failed',
					'response.incomplete',
					'error',
				}:
					response_timing.finish(event.type)
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
					for item in event.response.output:
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
					break
				elif event.type == 'response.failed':
					timer.mark_outcome('failed')
					log_stream_outcome(
						event.type,
						user_id,
						stream_manager.get_turn_id(),
						recursion_depth + 1,
						connection_id,
						posthog_session_id,
						event,
					)
					await send_agent_ws_response(
						user_id,
						connection_id,
						create_ws_error_response(
							'I could not generate a response. '
							'Please try again.'
						),
					)
					return
				elif event.type == 'response.incomplete':
					timer.mark_outcome('incomplete')
					log_stream_outcome(
						event.type,
						user_id,
						stream_manager.get_turn_id(),
						recursion_depth + 1,
						connection_id,
						posthog_session_id,
						event,
					)
					await send_agent_ws_response(
						user_id,
						connection_id,
						create_ws_warning_response(
							'This response is incomplete. '
							'Please try again.'
						),
					)
					return
				elif event.type == 'error':
					timer.mark_outcome('failed')
					log_stream_outcome(
						event.type,
						user_id,
						stream_manager.get_turn_id(),
						recursion_depth + 1,
						connection_id,
						posthog_session_id,
						event,
					)
					await send_agent_ws_response(
						user_id,
						connection_id,
						create_ws_error_response(
							'The response was interrupted. '
							'Please try again.'
						),
					)
					return
		response_timing.finish('interrupted')

	# Stream closed
	if not completed:
		timer.mark_outcome('interrupted')
		log_stream_outcome(
			'interrupted',
			user_id,
			stream_manager.get_turn_id(),
			recursion_depth + 1,
			connection_id,
			posthog_session_id,
		)
		await send_agent_ws_response(
			user_id,
			connection_id,
			create_ws_error_response(
				'The response was interrupted. Please try again.'
			),
		)
		return

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


def _get_agent_system_prompt() -> str:
	return AGENT_SYSTEM_PROMPT + '\n\n' + AGENT_BEHAVIOUR_PROMPT
