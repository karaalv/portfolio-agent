"""Unit tests for user activity changes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from users.update import update_last_active

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'modified, expected', [(1, True), (0, False)]
)
async def test_activity_update_uses_utc(
	modified, expected
) -> None:
	"""Persist UTC activity and report whether it changed."""
	now = datetime(2026, 1, 1, tzinfo=timezone.utc)
	collection = AsyncMock()
	collection.update_one.return_value = SimpleNamespace(
		modified_count=modified
	)
	with (
		patch(
			'users.update.get_collection',
			return_value=collection,
		),
		patch(
			'users.update.get_utc_datetime_now', return_value=now
		),
	):
		assert await update_last_active('id') is expected
	collection.update_one.assert_awaited_once_with(
		{'user_id': 'id'}, {'$set': {'last_active_at': now}}
	)
