"""Orchestrate planning and execution of corpus retrieval."""

from rag.query_executor import execute_rag
from rag.query_planner import plan_rag


async def fetch_context(
	user_id: str, user_input: str, verbose: bool = False
) -> str:
	"""Retrieve grounded context for a visitor request."""
	query_plan = await plan_rag(user_id, user_input, verbose)
	return await execute_rag(query_plan, user_input, verbose)
