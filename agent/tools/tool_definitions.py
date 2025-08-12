"""
This module contains the tool definitions 
for the agent.
"""
import textwrap
from openai.types.responses import ToolParam

agent_tools: list[ToolParam] = [
    # RAG System Tool
    {
        "type": "function",
        "name": "fetch_context",
        "description": textwrap.dedent("""
            A tool for retrieving contextually relevant
            information from the Retrieval-Augmented Generation
            (RAG) system.

            This tool must be used whenever the user's request
            requires specific knowledge about Alvin Karanja,
            including details about his background, experience,
            projects, or any profile-related information.

            Do not attempt to answer such questions based on
            general knowledge or assumptions—always invoke this
            tool to ensure the response is accurate, grounded,
            and context-aware.

            The tool returns content that enables the agent to
            respond as Alvin with informed, precise answers.
        """),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": (
                        "The user's input exactly as received, "
                        "verbatim. This is used to trigger the "
                        "appropriate retrieval process."
                    )
                }
            },
            "required": ["user_input"],
            "additionalProperties": False
        }
    }
]