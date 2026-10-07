"""Exercise users against the testing MongoDB project."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.users.anonymous import AnonymousUser
from shared.ids import generate_uuid_str
from users.creation import create_user, push_user
from users.deletion import delete_user
from users.retrieval import does_user_exist, get_user
from users.update import update_last_active

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_create_and_retrieve_user(
	user_ids: list[str],
) -> None:
	"""Round-trip a generated identity and its UTC timestamps."""
	user = await create_user()
	user_ids.append(user.user_id)
	assert UUID(user.user_id).version == 4
	assert await does_user_exist(user.user_id)
	stored = await get_user(user.user_id)
	assert stored.user_id == user.user_id
	assert stored.created_at.tzinfo == timezone.utc
	# BSON dates retain milliseconds rather than microseconds.
	assert abs(stored.created_at - user.created_at) < timedelta(
		milliseconds=1
	)
	assert stored.last_active_at == stored.created_at
	collection = get_collection(MongoDBCollection.USERS)
	document = await collection.find_one(
		{'user_id': user.user_id}
	)
	assert document is not None
	assert isinstance(document['created_at'], datetime)
	assert isinstance(document['last_active_at'], datetime)


async def test_push_and_update_user(user_ids: list[str]) -> None:
	"""Update old activity while preserving the creation date."""
	user_id = generate_uuid_str()
	user_ids.append(user_id)
	old = datetime(2020, 1, 1, tzinfo=timezone.utc)
	user = AnonymousUser(
		user_id=user_id, created_at=old, last_active_at=old
	)
	assert await push_user(user) is user
	assert await update_last_active(user_id)
	stored = await get_user(user_id)
	assert stored.created_at == old
	assert stored.last_active_at > old
	assert stored.last_active_at.tzinfo == timezone.utc


async def test_delete_user(user_ids: list[str]) -> None:
	"""Remove a user and report repeated deletion as missing."""
	user = await create_user()
	user_ids.append(user.user_id)
	assert await delete_user(user.user_id)
	assert not await does_user_exist(user.user_id)
	assert not await delete_user(user.user_id)
	with pytest.raises(ValueError, match='not found'):
		await get_user(user.user_id)


async def test_missing_user_operations(
	user_ids: list[str],
) -> None:
	"""Report missing users without inserting records."""
	user_id = generate_uuid_str()
	assert not await does_user_exist(user_id)
	assert not await update_last_active(user_id)
	assert not await delete_user(user_id)
	with pytest.raises(ValueError, match='not found'):
		await get_user(user_id)
