"""
This module contains the Input Refiner
and Query Planner for the RAG system.
"""

import textwrap

from agent.memory.retrieval import retrieve_agent_memory_prompt
from common.utils import (
	TerminalColors,
	handle_exceptions_async,
)
from openai_client.main import (
	text_response,
	structured_response,
)
from openai_client.models import OpenAILanguageModel
from rag.schemas import QueryPlan

# --- Constants ---

_refiner_model = OpenAILanguageModel.GPT_6_LUNA
_planner_model = OpenAILanguageModel.GPT_6_1_SOL

# --- Input Refiner ---


@handle_exceptions_async('rag.query_planner: Input Refiner')
async def input_refiner(
	user_id: str, user_input: str, verbose: bool = False
) -> str:
	"""
	Refine the user input by reformating the
	original prompt with relevant context.
	"""
	history = await retrieve_agent_memory_prompt(user_id)

	system_prompt = textwrap.dedent(f"""
        You are an expert input refiner for a portfolio site
        with a Retrieval-Augmented Generation (RAG) agent.
        It interacts with visitors, recruiters, and
        collaborators.

        Refine the user input by blending in only relevant
        context from their conversation history. The goal is
        to make the request clearer, more specific, and more
        useful for downstream RAG retrieval and planning.

        This is a low-level text improvement task — not a
        rewriting, generation, or reasoning task.

        Rules:
        - Preserve the user's original intent, meaning, and
        tone exactly.
        - Use the conversation history only to lightly
        supplement the input — never override or replace it.
        - Fix grammar, structure, and clarity where needed.
        - You may add scope, clarifications, or specific
        terminology *only* if it is clearly implied by the
        conversation history.
        - Do not introduce new ideas, assumptions, or
        speculative context.
        - Do not ask the user for more information or offer
        suggestions.
        - The output must be a single, refined version of the
        users input — no alternatives, no meta comments,
        no surrounding explanations.

        Your role is to clean and clarify — not to resolve
        ambiguity or generate content.

        Conversation history:
        {history}
    """)

	if verbose:
		print(
			f'{TerminalColors.cyan}'
			f'Refining input with context:\n'
			f'{TerminalColors.reset}'
			f'{history}\n'
		)

	return await text_response(
		system_prompt=system_prompt,
		user_prompt=user_input,
		model=_refiner_model,
	)


# --- Query Planner ---


@handle_exceptions_async('rag.query_planner: Query Planner')
async def query_planner(refined_input: str) -> QueryPlan:
	"""
	Plan the query by breaking it down
	into sub-queries.
	"""
	system_prompt = textwrap.dedent("""
        You are an expert query planner for a portfolio site
        with a Retrieval-Augmented Generation (RAG) agent.
        It interacts with visitors, recruiters, and
        collaborators.

        Your role is to break the refined user input into a
        set of focused sub-queries that, together, enable
        comprehensive, context-aware retrieval.

        Goals:
        - Each sub-query must explore a distinct aspect or
        related idea, DO NOT REPEAT SEMANTIC SEARCH SPACES.
        - Only include a sub-query if it adds new information
        not covered by others.
        - Ensure related concepts are explored to maximise
        semantic coverage.
        - Avoid redundancy; no two sub-queries should overlap.
        - Include clarifying sub-queries if the request is
        ambiguous.
        - Sub-queries must be succinct and use wording that is
        more likely to get a strong semantic match.
        - Limit to a maximum of 3 sub-queries.
        - Base all queries strictly on provided input and
        context — never invent facts.

        The output will be structured separately; focus only
        on producing the most effective sub-queries for
        retrieval.
    """)

	query_plan = await structured_response(
		system_prompt=system_prompt,
		user_prompt=refined_input,
		response_format=QueryPlan,
		model=_planner_model,
	)

	return query_plan
