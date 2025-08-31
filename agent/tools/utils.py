"""
This module contains utility functions
for the agent tools.
"""

from common.utils import (
	TerminalColors,
	handle_exceptions_async,
)
from openai_client.main import agent_search

# --- Constants ---

_researcher_model = 'gpt-4.1-mini'

# --- Utilities ---


@handle_exceptions_async('agent.tools.utils: Researcher')
async def researcher(orchestrator_input: str, verbose: bool = False) -> str:
	"""
	Perform research based on the user's input.
	This function uses the researcher model to
	generate a response.
	"""
	response = await agent_search(
		search_query=orchestrator_input,
		model=_researcher_model,
	)

	if verbose:
		print(
			f'{TerminalColors.cyan}'
			f'\nResearcher Output:\n'
			f'{TerminalColors.reset}'
			f'{response}'
		)

	return response.strip()
