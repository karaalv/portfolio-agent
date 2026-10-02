"""Create and persist anonymous user records."""

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.users.anonymous import AnonymousUser
from shared.ids import generate_uuid_str
from shared.time import get_utc_datetime_now
from users.retrieval import does_user_exist


async def create_user() -> AnonymousUser:
	"""Generate an anonymous identity and store its record."""
	user_id = generate_uuid_str()
	if await does_user_exist(user_id):
		raise ValueError(f'User with ID {user_id} already exists.')

	now = get_utc_datetime_now()
	user = AnonymousUser(
		user_id=user_id,
		last_active_at=now,
		created_at=now,
	)
	return await push_user(user)


async def push_user(user: AnonymousUser) -> AnonymousUser:
	"""Persist a supplied user record and return it."""
	collection = get_collection(MongoDBCollection.USERS)
	await collection.insert_one(user.model_dump())
	return user
