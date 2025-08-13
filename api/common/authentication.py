"""
This module contains all logic related to 
authentication for the API.
"""
import os
import jwt
from fastapi import Request, HTTPException, WebSocket

# --- User Token JWT Authentication ---

def _validate_jwt(token: str):
    """
    Validates the JWT token.

    Args:
        token (str): The JWT token to validate.

    Returns:
        dict: The decoded JWT payload if valid, 
        else raises HTTPException.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="User authentication token is missing."
        )

    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET"),
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="User authentication token has expired."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user authentication token."
        )

def verify_jwt(request: Request):
    """
    Verifies the JWT token from the request.
    This token is used to verify users.

    Args:
        request (Request): The FastAPI request 
        object.
    """
    token = request.cookies.get("JWT", "")
    _validate_jwt(token)
    
def verify_jwt_ws(ws: WebSocket):
    """
    Verifies the JWT token from the websocket
    request.

    Args:
        ws (WebSocket): The FastAPI websocket 
        object.
    """
    token = ws.cookies.get("JWT", "")
    print(f"Verifying JWT token: {token}")
    _validate_jwt(token)

# --- Frontend Token Authentication ---

def _validate_frontend_token(token: str):
    """
    Validates the frontend token.

    Args:
        token (str): The frontend token to validate.

    Returns:
        dict: The decoded frontend token payload if valid,
        else raises HTTPException.
    """
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Frontend token is missing."
        )

    try:
        payload = jwt.decode(
            token,
            os.getenv("FRONTEND_SECRET"),
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=403,
            detail="Frontend token has expired."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=403,
            detail="Invalid frontend token."
        )

def verify_frontend_token(request: Request):
    """
    Verifies the frontend token from the request.
    This is used to ensure that the request is coming
    from a trusted frontend.

    Args:
        request (Request): The FastAPI request object.
    """
    token = request.headers.get("frontend-token", "")
    _validate_frontend_token(token)

def verify_frontend_token_ws(ws: WebSocket):
    """
    Verifies the frontend token from the websocket
    request.

    Args:
        ws (WebSocket): The FastAPI websocket object.
    """
    token = ws.headers.get("frontend-token", "")
    _validate_frontend_token(token)