"""
This module contains test cases for the 
server connection (testing server).
"""
import httpx

# --- Tests --- 

async def test_server_connection():
    """
    Test the server connection.
    It should establish a connection
    and return a successful response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            "http://127.0.0.1:9001/api/health",
            headers=None,
            json=None
        )

    assert response.status_code == 200, \
        "Server connection failed. Expected 200 status."

async def test_server_refusal():
    """
    Test the server refusal.
    It should reject unauthorized requests
    and return an error response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            "http://127.0.0.1:9001/api/users/session",
            headers=None,
            json=None
        )

    assert response.status_code == 403, \
        "Server refusal failed. Expected status code 403."