"""
Main module for utility functions used in tests.
"""
import os
import jwt
import httpx
from httpx import Response
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from api.common.schemas import APIResponse

# --- Authentication Utilities ---

def create_jwt_token() -> str:
    """
    Create a JWT token for testing.
    This token is used to authenticate
    requests to the API during tests.
    Token is valid for 1 minute.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=1)
    data = {
        "user_id": "test_user",
        "exp": exp,
    }
    return jwt.encode(
        data,
        str(os.getenv("JWT_SECRET")),
        algorithm="HS256"
    )

def create_frontend_token() -> str:
    """
    Create a frontend token for testing.
    This token is used to authenticate
    requests from the frontend during tests.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=1)
    data = {
        "user_id": "test_user",
        "exp": exp,
    }
    return jwt.encode(
        data,
        str(os.getenv("FRONTEND_SECRET")),
        algorithm="HS256"
    )

# --- Request Utilities ---

async def server_fetch(
    endpoint: str,
    method: str,
    parsed: bool = True,
    user_id: Optional[str] = None,
    jwt: Optional[str] = None,
    body: Optional[Any] = None
) -> Response | APIResponse:
    """
    Fetch data from the server for testing.
    This function simulates a request to the API
    and returns the response.

    Args:
        endpoint (str): The API endpoint to fetch.
        method (str): The HTTP method to use.
        user_id (Optional[str]): The user ID for authentication.
        jwt (Optional[str]): The JWT token for authentication.

    Returns:
        APIResponse: The response from the server.
    """
    # Set Header
    header = {
        "Content-Type": "application/json",
        "Frontend-Token": create_frontend_token(),
    }
    if user_id and jwt:
        header["Cookie"] = f"JWT={jwt};UUID={user_id}"
    url = f"http://127.0.0.1:9001{endpoint}"

    # Simulate a request to the server
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            headers=header,
            json=body
        )
    
    if not parsed:
        return response
    else:
        return APIResponse(**response.json())