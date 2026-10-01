"""
This module contains the main logic
for handling user-related operations.
"""

import uuid
from datetime import datetime, timezone

from common.utils import handle_exceptions_async
from schemas.users.anonymous import AnonymousUser
from users.database import does_user_exist_db, push_user

# --- User Creation ---


@handle_exceptions_async('users.main: Create User')
async def create_user() -> AnonymousUser:
	"""
	Creates a new user by generating a
	unique user ID

	Returns:
		AnonymousUser: The created user record.
	"""
	user_id = str(uuid.uuid4())

	if await does_user_exist_db(user_id):
		raise ValueError(f'User with ID {user_id} already exists.')

	now = datetime.now(timezone.utc)
	user = AnonymousUser(
		user_id=user_id,
		last_active_at=now,
		created_at=now,
	)
	await push_user(user)
	return user


# --- User Inspection ---


@handle_exceptions_async('users.main: Does User Exist')
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
