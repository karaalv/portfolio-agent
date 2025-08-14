"""
This module contains utility functions
for the agent tools.
"""
import textwrap
from common.utils import handle_exceptions_async, TerminalColors
from openai_client.main import agent_response

# --- Constants ---

_researcher_model = "gpt-4.1-mini"

# --- Utilities ---

@handle_exceptions_async("agent.tools.utils: Researcher")
async def researcher(
    orchestrator_input: str,
    verbose: bool = False
) -> str:
    """
    Perform research based on the user's input.
    This function uses the researcher model to
    generate a response.
    """
    system_prompt = textwrap.dedent(f"""
        You are an expert researcher for a portfolio site
        with a Retrieval-Augmented Generation (RAG) agent.
        Your role is to perform targeted research based on
        the input and return a precise, relevant, and
        factually accurate summary.

        You are part of a document creation pipeline. Your
        task is to gather supplementary, job-related
        information that will directly support creating a
        high-quality, tailored document.

        Scenarios:
        1. If provided with an exact URL, search and extract
        only the information from that link that is
        relevant to the task.
        2. If asked to research a company, gather factual
        details about its mission, vision, values, key
        offerings, and other relevant public information.

        The prompt you receive comes from an orchestrator
        LLM. It may include links, entities to research, and
        the purpose of the search. Follow the orchestrator's
        instructions exactly and focus only on what is
        necessary for the document creation goal.

        Guidelines:
        - Keep responses concise, factual, and on-topic.
        - Do not add speculation or unrelated details.
        - Preserve factual accuracy; cite directly from
        reliable sources when possible.
        - If no relevant information can be found, clearly
        state: "No relevant information found."

        Your output must be directly useful for the next
        stage of the pipeline, without extra commentary.
    """)

    response = await agent_response(
        system_prompt=system_prompt,
        user_input=orchestrator_input,
        model=_researcher_model,
        tools=[{"type": "web_search_preview"}]
    )

    output: str = response.output_text # type: ignore

    if verbose:
        print(
            f"{TerminalColors.cyan}"
            f"Researcher Output:"
            f"{TerminalColors.reset}"
            f"{output}"
        )
    return output