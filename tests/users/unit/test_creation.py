"""Unit tests for anonymous user creation and persistence."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from schemas.users.anonymous import AnonymousUser
from users.creation import create_user, push_user

pytestmark = pytest.mark.unit


async def test_create_user_uses_one_utc_timestamp() -> None:
	"""Use equal creation and activity dates for new users."""
	now = datetime(2026, 1, 1, tzinfo=timezone.utc)
	collection = AsyncMock()
	with (
		patch(
			'users.creation.generate_uuid_str', return_value='id'
		),
		patch(
			'users.creation.get_utc_datetime_now',
			return_value=now,
		),
		patch(
			'users.creation.does_user_exist', return_value=False
		),
		patch(
			'users.creation.get_collection',
			return_value=collection,
		),
	):
		user = await create_user()
	assert user.user_id == 'id'
	assert user.created_at == user.last_active_at == now
	document = collection.insert_one.call_args.args[0]
	assert isinstance(document['created_at'], datetime)
	collection.insert_one.assert_awaited_once()


async def test_create_user_rejects_duplicate_identity() -> None:
	"""Reject generated identities that already exist."""
	with (
		patch(
			'users.creation.generate_uuid_str', return_value='id'
		),
		patch(
			'users.creation.does_user_exist', return_value=True
		),
		patch('users.creation.get_collection') as collection,
	):
		with pytest.raises(ValueError, match='already exists'):
			await create_user()
	collection.assert_not_called()


async def test_push_user_propagates_database_failure() -> None:
	"""Propagate failed inserts to the caller."""
	collection = AsyncMock()
	collection.insert_one.side_effect = RuntimeError(
		'Insert failed'
	)
	with patch(
		'users.creation.get_collection', return_value=collection
	):
		with pytest.raises(RuntimeError, match='Insert failed'):
			await push_user(AnonymousUser(user_id='id'))
