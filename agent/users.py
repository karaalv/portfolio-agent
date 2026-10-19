from schemas.users.anonymous import AnonymousUser
from users.creation import create_user
from users.retrieval import does_user_exist, get_user


async def ensure_user_exists(user_id: str) -> AnonymousUser:
	if not await does_user_exist(user_id):
		# TODO: Publish user creation event
		return await create_user()
	return await get_user(user_id)
