"""
This module acts as the main interface
for the agent, wrapping all memory, tools
and components into a cohesive system.
"""
from agent import memory
from agent.memory.schemas import AgentMemory, AgentCanvas
from common.utils import TerminalColors, handle_exceptions_async, get_timestamp
from openai_client.main import agent_response
from agent.memory.main import push_memory, retrieve_memory
from agent.tools.tool_definitions import agent_tools
from openai.types.responses import ResponseOutputItem

# --- Constants ---

RECURSION_LIMIT = 3

# --- Resolvers ---

# TODO: Implement resolvers for agent logic

# --- Memory and Prompting --- 

@handle_exceptions_async("agent.main: Getting system prompt")
async def get_system_prompt(
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

    memory = await retrieve_memory(user_id, to_str=True)

    if verbose:
        print(
            f"{TerminalColors.magenta}"
            f"Retrieved memory for user {user_id}: \n"
            f"{TerminalColors.reset}"
            f"{memory}"
        )

    system_prompt = f"""
        You are an AI impersonation of Alvin Karanja for my
        portfolio site. I am a software engineer, machine
        learning engineer, and data scientist, recently
        graduated from Imperial College London. Answer as if
        you are me, engaging visitors who want to learn about
        my profile, projects, or experience for potential
        roles, collaborations, or general interest.

        Be polite and formal, with only occasional, subtle
        lighthearted humour. You are a RAG agent: for queries
        requiring my specific knowledge, retrieve context from
        tools and respond in character.

        You can also use tools to generate custom resumes or
        cover letters if the user provides a job description
        and company details—refer to tool docs for usage.

        Only use RAG when retrieval is required for relevance
        and accuracy. Personality or belief notes from
        retrievals should not change tone, but may guide the
        conversation.

        If the user has chatted before, their history is here:
        {memory}

        Note: Chat history is deleted after 7 days of inactivity
        to manage platform data.
    """

    return system_prompt

@handle_exceptions_async("agent.main: Chat")
async def chat(
    user_id: str,
    input: str,
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
    if recursion_count >= RECURSION_LIMIT:
        return """
            Sorry I have reached my limit for processing 
            this request, please try again later.
        """

    # Push user input to memory
    await push_memory(
        user_id=user_id, 
        source='user', 
        content=input
    )

    # Get system prompt
    system_prompt = await get_system_prompt(
        user_id=user_id,
        verbose=verbose
    )

    # Call OpenAI API
    response = await agent_response(
        system_prompt=system_prompt, 
        user_input=input,
        tools=agent_tools
    )

    if response.type == "message":
        message = response.content[0].text.strip()  # type: ignore
        
        await push_memory(
            user_id=user_id,
            source='agent',
            content=message
        )
        return message
    elif response.type == "function_call":
        # function call response
        name, args = response.name, response.arguments
        return f"""
            {name}({', '.join(args)})
        """
    else: 
        # unknown response type
        raise ValueError(
            f"Unknown response type: "
            f"{response.type}"
        )