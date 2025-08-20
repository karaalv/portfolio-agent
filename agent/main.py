"""
This module acts as the main interface
for the agent, wrapping all memory, tools
and components into a cohesive system.
"""
import textwrap
import json
import asyncio
from typing import Optional, Any
from common.utils import TerminalColors, handle_exceptions_async
from openai_client.main import agent_response
from agent.memory.main import push_memory, push_canvas_memory, retrieve_memory
from agent.memory.compressor import update_user_summarisation
from agent.tools.tool_definitions import agent_tools
from users.database import update_last_active
# Tools
from rag.main import fetch_context
from agent.tools.main import generate_resume, generate_letter
# Monitoring
from monitoring.main import check_usage_limit, inform_user_usage_limit

# --- Constants ---

_RECURSION_LIMIT = 3
_agent_model = "gpt-4.1-mini"

# --- Resolvers ---

@handle_exceptions_async("agent.main: Execute Tool")
async def _execute_tool(
    user_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    verbose: bool
) -> str:
    """
    This function executes the agent
    tool with the given arguments.
    """
    recursive_prompt = textwrap.dedent(f"""
        The following is information retrieved using one of my
        tools in response to the user's request. It provides
        relevant context or details needed to continue the
        conversation naturally.

        Using this information, respond in character as Alvin
        Karanja—maintaining tone, clarity, and accuracy—
        and continue the conversation as if this knowledge
        was already mine.

        Avoid mentioning tools or retrievals. Focus on
        answering the user's original query based on the
        content provided below.

        Tool result:\n
    """)

    tool_result = ''

    if tool_name == "fetch_context":
        tool_result = await fetch_context(
            user_id=user_id,
            user_input=tool_args['user_input'],
            verbose=verbose
        )

    elif tool_name == "generate_resume":
        tool_result = await generate_resume(
            user_id=user_id,
            context_seed=tool_args['context_seed'],
            verbose=verbose
        )
        # Push results to memory
        # DO NOT WAIT
        asyncio.create_task(
            push_canvas_memory(
                user_id=user_id,
                agent_response=tool_result['response'],
                canvas_content=tool_result['resume'],
                title=tool_result['title']
            )
        )

        return ""
    elif tool_name == "generate_letter":
        tool_result = await generate_letter(
            user_id=user_id,
            context_seed=tool_args['context_seed'],
            verbose=verbose
        )
        # Push results to memory
        # DO NOT WAIT
        asyncio.create_task(
            push_canvas_memory(
                user_id=user_id,
                agent_response=tool_result['response'],
                canvas_content=tool_result['letter'],
                title=tool_result['title']
            )
        )

        return ""
    else:
        return """
            The tool requested was not recognized,
            try again and be more careful with the
            tool invocation.
        """
    
    if verbose:
        print(
            f"{TerminalColors.blue}"
            f"\n--- Tool result for {tool_name}---\n"
            f"{TerminalColors.reset}"
            f"{tool_result.strip()}"
        )

    return recursive_prompt + tool_result.strip()

# --- Memory and Prompting --- 

@handle_exceptions_async("agent.main: Getting system prompt")
async def _get_system_prompt(
    user_id: str,
    verbose: bool = False
) -> str:
    """
    Constructs the system prompt for the agent
    using the context of the conversation history
    for the user.

    Args:
        user_id (str): The ID of the user.

    Returns:
        str: The constructed system prompt.
    """

    memory = await retrieve_memory(
        user_id, 
        to_str=True,
        drop_canvas=True
    )

    if verbose:
        print(
            f"{TerminalColors.magenta}"
            f"Retrieved memory for user {user_id}: \n"
            f"{TerminalColors.reset}"
            f"{memory}"
        )

    system_prompt = textwrap.dedent(f"""
        You are impersonating Alvin Karanja on his portfolio 
        site. Respond as if you are him when engaging visitors 
        about his profile, projects, or experience for potential 
        roles, collaborations, or general interest.

        Be polite and formal, with only occasional, subtle 
        lighthearted humour.

        You are a RAG agent. For queries needing Alvin's 
        knowledge, use retrieval tools. Use context to inform 
        answers, but never change tone.

        You can also use tools to generate resumes or cover 
        letters if the user provides a job description and 
        company details. Always use tools for these requests.

        Users may reach their generation limit. If so, tell 
        them politely they must wait 1 week before generating 
        new content. Reassure them they can still chat with you 
        for regular Q&A.

        Tell users they can navigate to the 'info' section in 
        the navbar for more details on engaging with the chat 
        bot.

        If the user has chatted before, their history is here: 
        {memory}
    """)

    return system_prompt

@handle_exceptions_async("agent.main: Chat")
async def chat(
    user_id: str,
    ip: str,
    ua: str,
    input: str,
    recursive_prompt: Optional[str] = None,
    recursion_count: int = 0,
    verbose: bool = False
) -> str:
    """
    Handles the chat interaction with users, 
    processing their input and resolving tools
    accordingly.

    Args:
        user_id (str): The ID of the user.
        input (str): The user's input message.
        recursion_count (int, optional): The current 
        recursion depth.

    Returns:
        str: The agent's response message.
    """
    if recursion_count >= _RECURSION_LIMIT:
        return """
            Sorry I have reached my limit for processing 
            this request, please try again later.
        """

    # Push user input to memory on 
    # initial pass, update timestamp
    if recursion_count == 0:
        await push_memory(
            user_id=user_id, 
            source='user', 
            content=input
        )

        asyncio.create_task(
            update_last_active(user_id)
        )

    # Get system prompt, if call is 
    # recursive, add context from 
    # tool result
    system_prompt = await _get_system_prompt(
        user_id=user_id,
        verbose=verbose
    )

    if recursive_prompt:
        system_prompt += f"\n\n{recursive_prompt}"

    # Call OpenAI API
    response = await agent_response(
        system_prompt=system_prompt, 
        user_input=input,
        tools=agent_tools,
        model=_agent_model
    )

    if response.type == "message":
        message = response.content[0].text.strip() # type: ignore
        
        await push_memory(
            user_id=user_id,
            source='agent',
            content=message
        )

        # Update user summarisation in background
        # DO NOT AWAIT
        asyncio.create_task(update_user_summarisation(user_id))

        return message
    elif response.type == "function_call":
        # function call response
        tool_name: str = response.name
        tool_args: dict[str, Any] = json.loads(response.arguments)

        # Check if user has exceeded usage limit
        if not await check_usage_limit(
            user_id=user_id,
            ip=ip,
            ua=ua
        ):
            usage_response = await inform_user_usage_limit()
            return usage_response

        tool_result = await _execute_tool(
            user_id=user_id,
            tool_name=tool_name,
            tool_args=tool_args,
            verbose=verbose
        )

        if (
            tool_name == "generate_resume" or 
            tool_name == "generate_letter"
        ):
            return ""

        return await chat(
            user_id=user_id,
            ip=ip,
            ua=ua,
            input=input,
            recursive_prompt=tool_result,
            recursion_count=recursion_count + 1,
            verbose=verbose
        )
    else:
        # unknown response type
        raise ValueError(
            f"Unknown response type: "
            f"{response.type}"
        )