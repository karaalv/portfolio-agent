"""
This module contains all logic related to 
authentication for the API.
"""
import os
import jwt
from fastapi import Request, HTTPException

def verify_jwt(request: Request):
    """
    Verifies the JWT token from the request.
    This token is used to verify users.

    Args:
        request (Request): The FastAPI request 
        object.
    """
    token = request.cookies.get("JWT", "")

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
        return payload.get("user_id")
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

def verify_frontend_token(request: Request):
    """
    Verifies the frontend token from the request.
    This is used to ensure that the request is coming
    from a trusted frontend.

    Args:
        request (Request): The FastAPI request object.
    """
    token = request.headers.get("Frontend-Token", "")

    if not token:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid frontend token."
        )
    
    try:
        payload = jwt.decode(
            token, 
            os.getenv("FRONTEND_SECRET"), 
            algorithms=["HS256"]
        )
        return payload.get("nonce")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Frontend token has expired."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid frontend token."
        )