"""
Coordinate portfolio conversations, retrieval tools, and memory.
"""

import json
from typing import cast

from openai.types.responses import ResponseInputItemParam

from agent.memory.insertion import insert_agent_memory
from agent.memory.retrieval import retrieve_agent_memory_prompt
from agent.prompts.agent import AGENT_SYSTEM_PROMPT
from agent.prompts.behaviour import AGENT_BEHAVIOUR_PROMPT
from agent.prompts.tools import format_failed_tool_response
from agent.tools.dispatch import dispatch_tool
from agent.tools.tool_definitions import AGENT_TOOL_DEFINITIONS
from openai_client.main import agent_response
from schemas.agent.memory import AgentMemorySource
from shared.logging import rich_print
from users.database import update_last_active

_TOOL_ROUND_LIMIT = 3
_TOOL_LIMIT_MESSAGE = (
    'I could not retrieve enough information to answer this request. '
    'Please try a more specific question about Alvin or his work.'
)


async def chat(
    user_id: str, user_input: str, verbose: bool = False
) -> str:
    """Answer one turn and persist its input and final response.

    Allow up to three rounds of context retrieval. Load history before
    storing the current input so that input appears only once.
    """
    if not user_input.strip():
        raise ValueError('The user input must not be empty.')

    await update_last_active(user_id)
    memory_prompt = await retrieve_agent_memory_prompt(user_id)
    await insert_agent_memory(
        user_id, AgentMemorySource.USER, user_input
    )
    instructions = '\n\n'.join(
        (AGENT_SYSTEM_PROMPT, AGENT_BEHAVIOUR_PROMPT)
    )
    response_input: list[ResponseInputItemParam] = [
        {'role': 'user', 'content': memory_prompt},
        {'role': 'user', 'content': user_input},
    ]

    for round_number in range(_TOOL_ROUND_LIMIT + 1):
        response = await agent_response(
            system_prompt=instructions,
            user_prompt=response_input,
            tools=AGENT_TOOL_DEFINITIONS,
        )
        tool_calls = [
            item for item in response.output
            if item.type == 'function_call'
        ]
        if not tool_calls:
            message = response.output_text.strip()
            if not message:
                message = '\n'.join(
                    content.refusal
                    for item in response.output
                    if item.type == 'message'
                    for content in item.content
                    if content.type == 'refusal'
                ).strip()
            if not message:
                raise RuntimeError('The agent returned no answer.')
            break

        if round_number == _TOOL_ROUND_LIMIT:
            message = _TOOL_LIMIT_MESSAGE
            break

        # Preserve reasoning and call items for API continuation.
        response_input.extend(
            cast(
                ResponseInputItemParam,
                item.model_dump(exclude_none=True),
            )
            for item in response.output
        )
        for call in tool_calls:
            try:
                params = json.loads(call.arguments)
            except json.JSONDecodeError:
                result = format_failed_tool_response(
                    'Tool arguments must be a valid JSON object.'
                )
            else:
                if not isinstance(params, dict):
                    result = format_failed_tool_response(
                        'Tool arguments must be a JSON object.'
                    )
                else:
                    result = await dispatch_tool(
                        user_id=user_id,
                        tool_name=call.name,
                        tool_params=params,
                        user_input=user_input,
                    )
            response_input.append(
                {
                    'type': 'function_call_output',
                    'call_id': call.call_id,
                    'output': result,
                }
            )
        if verbose:
            rich_print(
                f'Completed retrieval round {round_number + 1}.',
                prefix='agent.main',
            )

    await insert_agent_memory(user_id, AgentMemorySource.AGENT, message)
    return message
