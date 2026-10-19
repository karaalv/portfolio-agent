"""Orchestrate planning and execution of corpus retrieval."""

from agent.streaming.delivery import send_agent_ws_response
from api.websocket.helpers.responses import (
	create_ws_agent_thinking_captions_response,
)
from rag.query_executor import execute_rag
from rag.query_planner import plan_rag


async def fetch_context(
	user_id: str,
	user_input: str,
	verbose: bool = False,
	connection_id: str | None = None,
) -> str:
	"""Retrieve grounded context for a visitor request."""
	query_plan = await plan_rag(user_id, user_input, verbose)
	await send_agent_ws_response(
		user_id,
		connection_id,
		create_ws_agent_thinking_captions_response(
			query_plan.agent_thinking_captions
		),
	)
	return await execute_rag(query_plan, user_input, verbose)
