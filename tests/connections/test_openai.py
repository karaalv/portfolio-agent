"""
This module tests connectivity with the 
OpenAI API.
"""
from pydantic import BaseModel, Field
from openai_client.main import (
    get_embedding, 
    normal_response, 
    structured_response, 
    agent_response
)
from openai.types.responses import ToolParam

# --- Tests ---

async def test_get_embedding():
    """
    Tests the OpenAI embedding functionality.
    """
    embedding = await get_embedding("Hello, world!")
    assert isinstance(embedding, list)
    assert len(embedding) > 0

async def test_normal_response():
    """
    Tests the OpenAI normal response functionality.
    """
    response = await normal_response(
        system_prompt="You are a helpful assistant.",
        user_input="What is the capital of France?"
    )
    assert isinstance(response, str)
    assert "Paris" in response

async def test_structured_response():
    """
    Tests the OpenAI structured response functionality.
    """
    class TestOpenAIClient(BaseModel):
        response: str = Field(
            ...,
            description="Response to the user query."
        )

    response = await structured_response(
        system_prompt="You are a helpful assistant.",
        user_input="Can you provide a summary of the latest news?",
        response_format=TestOpenAIClient
    )
    assert isinstance(response, TestOpenAIClient)

async def test_agent_response():
    """
    Tests the OpenAI agent response functionality.
    """
    # Agent tools example
    tools: list[ToolParam] = [{
        "type": "function",
        "name": "get_weather",
        "description": "Get current temperature for provided coordinates in celsius.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        },
        "strict": True
    }]

    # Test normal agent response
    response = await agent_response(
        system_prompt="You are a helpful assistant.",
        user_input="How are you",
        tools=tools
    )

    assert response.type == "message", "Response type should be 'message'."
    assert response.content[0].text is not None, "Response content should not be None." # type: ignore

    # Test function call response
    response = await agent_response(
        system_prompt="You are a helpful assistant.",
        user_input="What is the weather like in Paris?",
        tools=tools
    )

    assert response.type == "function_call", "Response type should be 'function_call'."
    assert response.name == "get_weather", "Function name should be 'get_weather'."