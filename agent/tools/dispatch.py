"""
Validate and dispatch the portfolio agent's retrieval tool calls.
"""

from typing import Any

from pydantic import ValidationError

from agent.prompts.tools import (
    format_failed_tool_response,
    format_successful_tool_response,
)
from rag.main import fetch_context


async def dispatch_tool(
    user_id: str,
    tool_name: str,
    tool_params: dict[str, Any],
    user_input: str,
) -> str:
    """
    Retrieve context using validated arguments
    and server-owned user ID.
    """
    # Validate tool name before proceeding
    if tool_name != 'fetch_context':
        return format_failed_tool_response(
            'Unknown tool. Only fetch_context is available.'
        )

    # Handle tool execution
    try:
        # TODO tool call and resolution
        return ''
    except Exception:
        return format_failed_tool_response(
            'Portfolio context retrieval is '
            'temporarily unavailable.'
        )
