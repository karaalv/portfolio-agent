"""Unit tests for user lookup and BSON date normalisation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from users.retrieval import does_user_exist, get_user

pytestmark = pytest.mark.unit


async def test_get_user_normalises_bson_dates() -> None:
	"""Restore timezone information on BSON UTC dates."""
	date = datetime(2026, 1, 1)
	collection = AsyncMock()
	collection.find_one.return_value = {
		'user_id': 'id',
		'created_at': date,
		'last_active_at': date,
	}
	with patch(
		'users.retrieval.get_collection', return_value=collection
	):
		user = await get_user('id')
	assert user.created_at == date.replace(tzinfo=timezone.utc)
	assert user.last_active_at.tzinfo == timezone.utc
	collection.find_one.assert_awaited_once_with(
		{'user_id': 'id'}, {'_id': 0}
	)


async def test_get_user_rejects_missing_identity() -> None:
	"""Raise when the database contains no matching user."""
	collection = AsyncMock()
	collection.find_one.return_value = None
	with patch(
		'users.retrieval.get_collection', return_value=collection
	):
		with pytest.raises(ValueError, match='not found'):
			await get_user('missing')


@pytest.mark.parametrize(
	'record, expected', [(None, False), ({}, True)]
)
async def test_user_exists_checks_presence(
	record, expected
) -> None:
	"""Use document presence, not document truthiness."""
	collection = AsyncMock()
	collection.find_one.return_value = record
	with patch(
		'users.retrieval.get_collection', return_value=collection
	):
		assert await does_user_exist('id') is expected
	collection.find_one.assert_awaited_once_with(
		{'user_id': 'id'}, {'_id': 1}
	)
