"""
This module contains operations
related to database interactions
for user management.
"""

from datetime import datetime, timezone

from common.utils import handle_exceptions_async
from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.users.anonymous import AnonymousUser

# --- Creation ---


@handle_exceptions_async('users.database: Pushing User')
async def push_user(user: AnonymousUser) -> AnonymousUser:
	"""
	Pushes a user to the MongoDB database.

	Args:
		user (AnonymousUser): The user object to be stored.

	Returns:
		AnonymousUser: The user object that was stored.
	"""
	collection = get_collection(MongoDBCollection.USERS)

	if collection is None:
		raise ConnectionError('MongoDB client is not connected.')

	await collection.insert_one(user.model_dump())
	return user


# --- Retrieval ---


@handle_exceptions_async('users.database: Retrieving User')
async def get_user(user_id: str) -> AnonymousUser:
	"""
	Retrieves a user from the MongoDB database
	by user ID.

	Args:
		user_id (str): The unique identifier
		for the user.

	Returns:
		AnonymousUser: The user object retrieved from
		the database.
	"""
	collection = get_collection(MongoDBCollection.USERS)

	if collection is None:
		raise ConnectionError('MongoDB client is not connected.')

	user_data = await collection.find_one({'user_id': user_id})

	if user_data is None:
		raise ValueError(f'User with ID {user_id} not found.')

	return AnonymousUser(**user_data)


# --- Inspection ---


@handle_exceptions_async('users.database: Checking User')
async def does_user_exist_db(user_id: str) -> bool:
	"""
	Checks if a user exists in the MongoDB database
	by user ID.

	Args:
		user_id (str): The unique identifier for the user.

	Returns:
		bool: True if the user exists, False otherwise.
	"""
	collection = get_collection(MongoDBCollection.USERS)

	if collection is None:
		raise ConnectionError('MongoDB client is not connected.')

	user = await collection.find_one({'user_id': user_id})
	return user is not None


# --- Modification ---


@handle_exceptions_async('users.database: Updating last active')
async def update_last_active(user_id: str) -> bool:
	"""
	Updates the last active timestamp for a user
	in the database.

	Args:
		user_id (str): The unique identifier
		for the user.

	Returns:
		bool: True if the update was successful,
		False otherwise.
	"""
	collection = get_collection(MongoDBCollection.USERS)

	if collection is None:
		raise ConnectionError('MongoDB client is not connected.')

	result = await collection.update_one(
		{'user_id': user_id},
		{'$set': {'last_active_at': datetime.now(timezone.utc)}},
	)

	return result.modified_count > 0


# --- Deletion ---


@handle_exceptions_async('users.database: Deleting User')
async def delete_user(user_id: str) -> bool:
	"""
	Deletes a user from the MongoDB database
	by user ID.

	Args:
		user_id (str): The unique identifier
		for the user.

	Returns:
		bool: True if the deletion was successful,
		False otherwise.
	"""
	collection = get_collection(MongoDBCollection.USERS)

	if collection is None:
		raise ConnectionError('MongoDB client is not connected.')

	result = await collection.delete_one({'user_id': user_id})
	return result.deleted_count > 0
