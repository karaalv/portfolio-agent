"""
This module contains the main logic
for handling user-related operations.
"""
import uuid
from users.schemas import User
from common.utils import handle_exceptions_async, get_timestamp
from users.database import push_user, does_user_exist_db

# --- User Creation ---

@handle_exceptions_async("users.main: Create User")
async def create_user() -> User:
    """
    Creates a new user by generating a
    unique user ID

    Returns:
        User: A unique identifier for the user.
    """
    user_id = str(uuid.uuid4())

    if await does_user_exist_db(user_id):
        raise ValueError(
            f"User with ID {user_id} already exists."
        )
    
    user = User(
        user_id=user_id,
        last_active=get_timestamp()
    )
    await push_user(user)
    return user

# --- User Inspection ---

@handle_exceptions_async("users.main: Does User Exist")
async def does_user_exist(user_id: str) -> bool:
    """
    Checks if a user exists in the database
    by their user ID.
    
    Args:
        user_id (str): The unique identifier for the user.
    
    Returns:
        bool: True if the user exists, False otherwise.
    """
    return await does_user_exist_db(user_id)