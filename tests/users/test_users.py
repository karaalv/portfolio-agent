"""
This module contains integration tests
for user-related operations.
"""
import pytest
from httpx import Response
from common.utils import TerminalColors
from database.mongodb.config import connect_mongo, close_mongo
from users.main import create_user
from tests.utils.main import server_fetch

# --- Config ---

@pytest.fixture(scope="function", autouse=True)
async def mongo_session():
    if not await connect_mongo():
        pytest.exit(
            f"{TerminalColors.red}"
            f"Failed to connect to MongoDB."
            f"{TerminalColors.reset}"
        )
    yield
    if not await close_mongo():
        pytest.exit(
            f"{TerminalColors.red}"
            f"Failed to close MongoDB connection."
            f"{TerminalColors.reset}"
        )

# --- Tests ---

async def test_create_user():
    """
    Test the user creation functionality.
    It should create a user and return a User object
    with a unique user_id and last_active timestamp.
    """
    user = await create_user()

    assert user.user_id is not None, \
    "User ID should not be None"

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