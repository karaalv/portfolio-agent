"""
This module contains the Input Refiner
and Query Planner for the RAG system.
"""
import textwrap
from rag.schemas import QueryPlan
from common.utils import handle_exceptions_async
from openai_client.main import normal_response, structured_response
from agent.memory.compressor import get_user_summarisation

# --- Constants ---

_refiner_model = "gpt-4.1-mini"
_planner_model = "gpt-4.1"

# --- Input Refiner ---

@handle_exceptions_async("rag.query_planner: Input Refiner")
async def input_refiner(
    user_id: str,
    user_input: str
) -> str:
    """
    Refine the user input by reformating the
    original prompt with relevant context.
    """
    summary = await get_user_summarisation(user_id)

    system_prompt = textwrap.dedent(f"""
        You are an expert input refiner for a portfolio site
        with a Retrieval-Augmented Generation (RAG) agent.
        It interacts with visitors, recruiters, and
        collaborators.

        Refine the user input by blending in only relevant
        context from their conversation history. The goal is
        to make the request clearer, more specific, and more
        useful for RAG retrieval.

        Rules:
        - The original intent and meaning of the request must
        be preserved.
        - Use the conversation summary only to supplement the
        request, never to replace or override it.
        - Add missing details only when they are implied by
        the context.
        - Avoid introducing unrelated or speculative content.
        - The output should be a single, optimised version of
        the request — do not give multiple options or any
        extra commentary.

        Conversation summary:
        {summary}
    """)

    return await normal_response(
        system_prompt=system_prompt,
        user_input=user_input,
        model=_refiner_model
    )

# --- Query Planner ---

@handle_exceptions_async("rag.query_planner: Query Planner")
async def query_planner(
    refined_input: str
) -> QueryPlan:
    """
    Plan the query by breaking it down 
    into sub-queries.
    """
    system_prompt = textwrap.dedent(f"""
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
        - Limit to a maximum of 5 sub-queries, unless the query
        is complicated use 2.
        - Base all queries strictly on provided input and
        context — never invent facts.

        The output will be structured separately; focus only
        on producing the most effective sub-queries for
        retrieval.
    """)

    query_plan = await structured_response(
        system_prompt=system_prompt,
        user_input=refined_input,
        response_format=QueryPlan,
        model=_planner_model
    )

    return query_plan