"""
This module acts as a client for 
interacting with the OpenAI API.
"""
import os
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import TypeVar, Type
from common.utils import handle_exceptions_async
from openai.types.responses import (
    ToolParam, 
    ResponseOutputItem
)

# --- Setup and Configuration ---

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_KEY")
)

# Generic type for pydantic models
PYDANTIC = TypeVar('PYDANTIC', bound=BaseModel)

# --- OpenAI Client Functions ---

@handle_exceptions_async("OpenAI: Get Embedding")
async def get_embedding(input: str) -> list[float]:
    """
    Returns the embedding for the given input
    using OpenAI's text-embedding-3-large model.
    """
    response = await client.embeddings.create(
        model="text-embedding-3-large",
        input=input
    )
    return response.data[0].embedding

@handle_exceptions_async("OpenAI: Normal Response")
async def normal_response(
    system_prompt: str,
    user_input: str,
    model: str = "gpt-4.1-nano"
) -> str:
    """ 
    Constructs a normal response from OpenAI.

    Args:
        system_prompt (str): The system prompt to guide the 
                            model.
        user_input (str): The user's input to the model.
        model (str): The model to use for the response.

    Returns:
        str: The response from the OpenAI client.
    """
    response = await client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_input
    )
    return response.output_text.strip()

@handle_exceptions_async("OpenAI: Structured Response")
async def structured_response(
    system_prompt: str,
    user_input: str,
    response_format: Type[PYDANTIC],
    model: str = "gpt-4.1-mini"
) -> PYDANTIC:
    """ 
    Constructs a structured response from OpenAI.

    Args:
        system_prompt (str): The system prompt to guide the 
                            model.
        user_input (str): The user's input to the model.
        response_format (Type[PYDANTIC]): The Pydantic 
            model to structure the response.
        model (str): The model to use for the response.

    Returns:
        PYDANTIC: The structured response from the OpenAI 
        client.
    """
    response = await client.responses.parse(
        model=model,
        text_format=response_format,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    if not response.output_parsed:
        raise ValueError(
            "Response parsing failed,"
            "Response from model is empty."
        )
    
    # Validate the response against the Pydantic model
    if not isinstance(response.output_parsed, response_format):
        raise ValueError(
            f"Response does not match expected"
            f" format: {response_format.__name__}"
        )
    
    return response.output_parsed

@handle_exceptions_async("OpenAI: Agent Response")
async def agent_response(
    system_prompt: str,
    user_input: str,
    tools: list[ToolParam],
    model: str = "gpt-4.1-nano"
) -> ResponseOutputItem:
    """ 
    Constructs an agent response from OpenAI.

    Args:
        system_prompt (str): The system prompt to guide the 
                            model.
        user_input (str): The user's input to the model.
        tools (List[ToolParam]): The tools available to the 
                                 agent.
        model (str): The model to use for the response.
    
    Returns:
        Response: The response from the OpenAI client.
    """
    response = await client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_input,
        tools=tools
    )

    if not response.output:
        raise ValueError(
            "Agent response is empty. "
            "Ensure the model is configured " \
            "correctly."
        )
    
    return response.output[0]

@handle_exceptions_async("OpenAI: Web Search")
async def agent_search(
    search_query: str,
    model: str = "gpt-4.1-mini"
) -> str:
    """
    Performs a web search using the specified model.
    """
    response = await client.responses.create(
        model=model,
        tools=[{"type": "web_search_preview"}],
        input=search_query
    )
    return response.output_text