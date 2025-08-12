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

refiner_model = "gpt-4.1-nano"
planner_model = "gpt-4.1-mini"

# --- Input Refiner ---

@handle_exceptions_async("RAG: Input Refiner")
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

        Refine the following user input by blending in 
        relevant context from their conversation history to 
        make it clearer, more specific, and useful for RAG 
        retrieval.

        Conversation summary:
        {summary}
    """)

    return await normal_response(
        system_prompt=system_prompt,
        user_input=user_input,
        model=refiner_model
    )

# --- Query Planner ---

@handle_exceptions_async("RAG: Query Planner")
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
        comprehensive and context-aware retrieval.

        Goals:
        - Capture the user's intent, entities, and any 
        constraints or timeframes.
        - Ensure each sub-query targets a distinct aspect of 
        the request.
        - Maximize semantic coverage, including relevant 
        synonyms or related terms.
        - Avoid redundancy between sub-queries.
        - Include clarifying sub-queries if the request is 
        ambiguous.
        - Base all queries strictly on provided input and 
        context — never invent facts.

        The output will be structured separately; focus only 
        on creating the most effective sub-queries for 
        retrieval.
    """)

    query_plan = await structured_response(
        system_prompt=system_prompt,
        user_input=refined_input,
        response_format=QueryPlan,
        model=planner_model
    )

    return query_plan