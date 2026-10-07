"""Validate context arguments before running RAG retrieval."""

from rag.main import fetch_context as retrieve_context
from schemas.agent.tools.context import FetchContextArguments


async def fetch_context(
	user_id: str,
	tool_args: str,
	verbose: bool = False,
) -> str:
	"""Retrieve context using validated model-supplied arguments.

	The user ID is supplied by the application, not the model.
	JSON parsing and schema errors propagate to the dispatcher.
	"""
	arguments = FetchContextArguments.model_validate_json(tool_args)
	return await retrieve_context(
		user_id=user_id,
		user_input=arguments.user_input,
		verbose=verbose,
	)
