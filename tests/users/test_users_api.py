"""
This module contains tests for user
related API endpoints.
"""
from httpx import Response
from tests.utils.main import server_fetch

# --- Tests ---

async def test_assigning_session():
    """
    Test assigning a user session to a new
    user and setting cookies, test making 
    sure an existing user session is not created.
    """
    # Test creating a new user session

    response_1: Response = await server_fetch(
        endpoint="/api/users/session",
        method="GET",
        parsed=False
    ) # type: ignore

    status_code_1: int = response_1.status_code
    cookies_1 = response_1.cookies
    
    assert status_code_1 == 201, \
        f"Expected status code 201, got {status_code_1}"
    
    uuid = cookies_1.get("UUID")
    jwt = cookies_1.get("JWT")

    assert uuid is not None, \
        "UUID cookie should be set"
    assert jwt is not None, \
        "JWT cookie should be set"
    
    # Test that a new user session is not created
    response_2: Response = await server_fetch(
        endpoint="/api/users/session",
        method="GET",
        parsed=False,
        user_id=uuid,
        jwt=jwt
    ) # type: ignore

    status_code_2: int = response_2.status_code

    assert status_code_2 == 200, \
        f"Expected status code 200, got {status_code_2}"