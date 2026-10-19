"""Retrieve anonymous users and check whether they exist."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.users.anonymous import AnonymousUser


async def get_user(user_id: str) -> AnonymousUser:
	"""Return a stored user or raise when the ID is not found."""
	collection = get_collection(MongoDBCollection.USERS)
	user_data = await collection.find_one(
		{'user_id': user_id}, {'_id': 0}
	)
	if user_data is None:
		raise ValueError(f'User with ID {user_id} not found.')
	return AnonymousUser.model_validate(user_data)


async def does_user_exist(user_id: str) -> bool:
	"""Return whether a record exists for the supplied ID."""
	collection = get_collection(MongoDBCollection.USERS)
	user = await collection.find_one({'user_id': user_id}, {'_id': 1})
	return user is not None
