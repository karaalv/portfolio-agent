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


# --- Retrieval ---

@handle_exceptions_async("users.database: Retrieving User")
async def get_user(user_id: str) -> User:
    """
    Retrieves a user from the MongoDB database 
    by user ID.
    
    Args:
        user_id (str): The unique identifier 
        for the user.
    
    Returns:
        User: The user object retrieved from 
        the database.
    """
    collection = get_collection("users")

    if collection is None:
        raise ConnectionError(
            "MongoDB client is not connected."
        )

    user_data = await collection.find_one({"user_id": user_id})
    
    if user_data is None:
        raise ValueError(f"User with ID {user_id} not found.")
    
    return User(**user_data)


# --- Inspection ---

@handle_exceptions_async("users.database: Checking User")
async def does_user_exist_db(user_id: str) -> bool:
    """
    Checks if a user exists in the MongoDB database 
    by user ID.
    
    Args:
        user_id (str): The unique identifier for the user.
    
    Returns:
        bool: True if the user exists, False otherwise.
    """
    collection = get_collection("users")

    if collection is None:
        raise ConnectionError(
            "MongoDB client is not connected."
        )

    user = await collection.find_one({"user_id": user_id})
    return user is not None