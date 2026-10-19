"""Log model outcomes and one timing summary per interaction."""

import json
from dataclasses import asdict

from openai.types.responses import ResponseStreamEvent

from agent.observability import AgentTimer
from shared.logging import log_error, log_info, log_warning
from shared.logging.context import log_properties


def log_turn_finished(
	timer: AgentTimer,
	user_id: str,
	turn_id: str,
	connection_id: str | None,
	posthog_session_id: str | None,
) -> None:
	"""Keep overlapping timings separate from wall-clock latency."""
	records = timer.records
	interaction = next(
		(
			record
			for record in records
			if record.scope == 'interaction'
		),
		None,
	)
	log_info(
		'agent_turn_finished',
		log_properties(
			'agent_turn_finished',
			user_id=user_id,
			posthog_session_id=posthog_session_id,
			turn_id=turn_id,
			connection_id=connection_id,
			status=timer.outcome,
			model=timer.model,
			interaction_duration_seconds=interaction.duration_seconds
			if interaction
			else None,
			openai_round_count=sum(
				record.scope == 'openai' for record in records
			),
			tool_call_count=sum(
				record.scope == 'tool' for record in records
			),
			timings_json=json.dumps(
				[asdict(record) for record in records]
			),
		),
	)


def log_stream_outcome(
	kind: str,
	user_id: str,
	turn_id: str,
	round_index: int,
	connection_id: str | None,
	posthog_session_id: str | None,
	event: ResponseStreamEvent | None = None,
) -> None:
	"""Log selected provider fields, never the full response/input."""
	names = {
		'response.failed': 'agent_response_failed',
		'response.incomplete': 'agent_response_incomplete',
		'error': 'agent_stream_error',
		'interrupted': 'agent_stream_interrupted',
	}
	response = getattr(event, 'response', None)
	error = getattr(response, 'error', None)
	incomplete = getattr(response, 'incomplete_details', None)
	name = names[kind]
	log = (
		log_warning
		if kind in {'response.incomplete', 'interrupted'}
		else log_error
	)
	log(
		name,
		log_properties(
			name,
			user_id=user_id,
			posthog_session_id=posthog_session_id,
			turn_id=turn_id,
			connection_id=connection_id,
			round_index=round_index,
			provider_event_type=kind,
			response_id=getattr(response, 'id', None),
			model=getattr(response, 'model', None),
			error_code=getattr(error, 'code', None)
			or getattr(event, 'code', None),
			error_message=getattr(error, 'message', None)
			or getattr(event, 'message', None),
			incomplete_reason=getattr(incomplete, 'reason', None),
		),
	)
