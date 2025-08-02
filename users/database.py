"""
This module contains operations 
related to database interactions
for user management.
"""
from users.schemas import User
from database.mongodb.main import get_collection
from common.utils import handle_exceptions_async

# --- Creation ---

@handle_exceptions_async("users.database: Pushing User")
async def push_user(user: User) -> User:
    """
    Pushes a user to the MongoDB database.
    
    Args:
        user (User): The user object to be stored.
    
    Returns:
        User: The user object that was stored.
    """
    collection = get_collection("users")

    if collection is None:
        raise ConnectionError(
            "MongoDB client is not connected."
        )

    await collection.insert_one(user.model_dump())
    return user