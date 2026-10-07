"""Unit tests for deletion of individual anonymous users."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from users.deletion import delete_user

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'deleted, expected', [(1, True), (0, False)]
)
async def test_delete_user_reports_result(
	deleted, expected
) -> None:
	"""Delete only the supplied identity and report removal."""
	collection = AsyncMock()
	collection.delete_one.return_value = SimpleNamespace(
		deleted_count=deleted
	)
	with patch(
		'users.deletion.get_collection', return_value=collection
	):
		assert await delete_user('id') is expected
	collection.delete_one.assert_awaited_once_with(
		{'user_id': 'id'}
	)
