"""
This module contains user routes for
the API.
"""
import os
from fastapi import APIRouter, Request
from users.schemas import User
from api.common.utils import api_exception_handler, create_jwt_token
from users.main import create_user, does_user_exist
from api.common.responses import success_response, error_response
from api.common.config import COOKIE_EXPIRY_SECONDS

# --- Constants ---

router = APIRouter()

# --- User Routes ---

@router.get("/session")
@api_exception_handler("Inspecting user session")
async def set_session(request: Request):
    """
    Sets a user session by creating a new user
    and setting a cookie with the user ID.
    """
    user_id: str = request.cookies.get("UUID", "")

    if not user_id:
        user: User = await create_user()

        response = success_response(
            message="User session created successfully.",
            data={"user_id": user.user_id},
            status_code=201
        )

        response.set_cookie(
            key="UUID",
            value=user.user_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=COOKIE_EXPIRY_SECONDS,
            expires=COOKIE_EXPIRY_SECONDS,
            domain=os.getenv("CORS_DOMAIN")
        )

        response.set_cookie(
            key="JWT",
            value=create_jwt_token(user.user_id),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=COOKIE_EXPIRY_SECONDS,
            expires=COOKIE_EXPIRY_SECONDS,
            domain=os.getenv("CORS_DOMAIN")
        )

        return response
    
    if not await does_user_exist(user_id):
        return error_response(
            message="User session does not exist.",
            status_code=404
        )

    return success_response(
        message="User session already exists.",
        data={"user_id": user_id},
        status_code=200
    )