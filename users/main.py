"""
This module contains the main logic
for handling user-related operations.
"""
import uuid
from users.schemas import User
from common.utils import handle_exceptions, get_timestamp
from users.database import push_user

# --- User Creation ---

@handle_exceptions("users.main: Create User")
async def create_user() -> User:
    """
    Creates a new user by generating a
    unique user ID

    Returns:
        User: A unique identifier for the user.
    """
    user = User(
        user_id=str(uuid.uuid4()),
        last_active=get_timestamp()
    )
    await push_user(user)
    return user