"""
This module contains tests for agent
related API endpoints.
"""
import pytest
from httpx import Response
from api.common.schemas import APIResponse
from tests.utils.main import server_fetch

# --- Constants ---

UUID = None
JWT = None

# --- Config ---

@pytest.fixture(scope="module", autouse=True)
async def setup_user_session():
    global UUID, JWT
    
    response: Response = await server_fetch(
        endpoint="/api/users/session",
        method="GET",
        parsed=False
    ) # type: ignore

    if response.status_code == 201:
        cookies = response.cookies
        UUID = cookies.get("UUID")
        JWT = cookies.get("JWT")
    else:
        pytest.fail(f"Failed to set up user session: {response.status_code}")

# --- Tests ---

async def test_frontend_auth():
    """
    Test that the agent API endpoints
    require frontend authentication.
    """
    response: Response = await server_fetch(
        endpoint="/api/agent/chat",
        method="POST",
        parsed=False
    )  # type: ignore

    status_code: int = response.status_code

    assert status_code == 401, \
        f"Expected status code 401, got {status_code}"
    
async def test_agent_chat():
    """
    Test the agent chat API endpoint.
    """
    body = {
        "input": "Hello, agent! This is a test message."
    }

    response: APIResponse = await server_fetch(
        endpoint="/api/agent/chat",
        method="POST",
        user_id=UUID,
        jwt=JWT,
        parsed=True,
        body=body
    )

    assert response.data is not None, \
        "Expected response data to be present"
    
async def test_agent_memory_retrieval():
    """
    Test the agent memory retrieval API endpoint.
    """
    response: APIResponse = await server_fetch(
        endpoint="/api/agent/memory",
        method="GET",
        user_id=UUID,
        jwt=JWT,
        parsed=True
    )

    assert response.data is not None, \
        "Expected response data to be present"

async def test_agent_memory_deletion():
    """
    Test the agent memory deletion API endpoint.
    """
    response: APIResponse = await server_fetch(
        endpoint="/api/agent/clear-memory",
        method="DELETE",
        user_id=UUID,
        jwt=JWT,
        parsed=True
    )

    assert response.metadata.success is True, \
        "Expected response metadata to indicate success"
