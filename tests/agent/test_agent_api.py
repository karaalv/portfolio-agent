"""
This module contains tests for agent
related API endpoints.
"""
import json
import pytest
import websockets
import httpx
from httpx import Response
from api.common.schemas import APIResponse, SocketResponse
from tests.utils.main import server_fetch, create_frontend_token
from agent.memory.main import push_memory
from database.mongodb.config import connect_mongo, close_mongo

# --- Constants ---

UUID = None
JWT = None

# --- Config ---

@pytest.fixture(scope="module", autouse=True)
async def setup_user_session():
    # Create test user
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
        pytest.fail(
            f"Failed to set up user session: "
            f"{response.status_code}"
        )
    # Create test message for deletion
    await connect_mongo()
    await push_memory(
        user_id=str(UUID),
        source='user',
        content='Test memory content'
    )
    await close_mongo()

# --- Tests ---

async def test_frontend_auth():
    """
    Test that endpoints are protected
    by client token.
    """
    url = f"http://127.0.0.1:9001/api/agent/memory"

    # Simulate a request to the server
    async with httpx.AsyncClient() as client:
        response = await client.request(
            url=url,
            method="GET",
        )

    status_code: int = response.status_code

    assert status_code == 403, \
        f"Expected status code 403, got {status_code}"

async def test_jwt_auth():
    """
    Test that the agent API endpoints
    require JWT authentication.
    """
    response: Response = await server_fetch(
        endpoint="/api/agent/memory",
        method="GET",
        parsed=False
    )

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

    url = "ws://127.0.0.1:9001/api/agent/ws/chat"
    headers = {
        'frontend-token': create_frontend_token(),
        'Cookie': f'JWT={JWT};UUID={UUID}'
    }

    async with websockets.connect(url, additional_headers=headers) as websocket:
        await websocket.send(json.dumps(body))
        response = await websocket.recv()

    response = SocketResponse(**json.loads(response))

    assert isinstance(response, SocketResponse), \
        "Expected response to be of type SocketResponse"

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
