"""
This module contains the main entry point
for the RAG system, orchestrating the overall
process.
"""

from common.utils import (
	TerminalColors,
	Timer,
	handle_exceptions_async,
)
from rag.query_executor import (
	refine_context,
	retrieve_documents_sequential,
)
from rag.query_planner import input_refiner, query_planner

# --- Main Orchestrator ---


@handle_exceptions_async('rag.main: fetch_context')
async def fetch_context(
	user_id: str, user_input: str, verbose: bool = False
) -> str:
	"""
	Fetch context for the user input by
	orchestrating the RAG pipeline.

	Args:
		user_id (str): The ID of the user.
		user_input (str): The input provided by the user.

	Returns:
		str: The augmented context for generation.
	"""
	timer = Timer(start=True)
	refined_input = await input_refiner(
		user_id=user_id,
		user_input=user_input,
		verbose=verbose,
	)
	refinement_time = timer.elapsed()

	query_plan = await query_planner(refined_input=refined_input)
	planning_time = timer.elapsed()

	retrieval_results = await retrieve_documents_sequential(
		user_id=user_id,
		query_plan=query_plan,
		streaming_context='agent_thinking',
		verbose=verbose,
	)
	retrieval_time = timer.elapsed()

	augmented_context = await refine_context(
		user_input=user_input,
		retrieval_results=retrieval_results,
	)
	augmentation_time = timer.elapsed()

	total_time = (
		refinement_time + planning_time + retrieval_time + augmentation_time
	)

	if verbose:
		print('\n--- RAG Pipeline Statistics ---\n')
		print(f'{TerminalColors.yellow}Pipeline Timing\n{TerminalColors.reset}')
		print(f'Refinement Time: {refinement_time:.4f} seconds')
		print(f'Planning Time: {planning_time:.4f} seconds')
		print(f'Retrieval Time: {retrieval_time:.4f} seconds')
		print(f'Augmentation Time: {augmentation_time:.4f} seconds')
		print(f'Total Pipeline Time: {total_time:.4f} seconds')
		print(
			f'{TerminalColors.yellow}\nPipeline Results\n{TerminalColors.reset}'
		)
		print(
			f'{TerminalColors.magenta}'
			f'Refined Input\n'
			f'{TerminalColors.reset}'
			f'{refined_input}'
		)
		print(
			f'{TerminalColors.magenta}'
			f'Query Plan\n'
			f'{TerminalColors.reset}'
			f'{query_plan}'
		)
		print(
			f'{TerminalColors.magenta}'
			f'Retrieval Results\n'
			f'{TerminalColors.reset}'
			f'{retrieval_results}'
		)
		print(
			f'{TerminalColors.magenta}'
			f'Augmented Context\n'
			f'{TerminalColors.reset}'
			f'{augmented_context}'
		)

	return augmented_context
