"""
This module contains integration tests
for user-related operations.
"""

import pytest

from common.utils import TerminalColors
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)
from users.main import create_user

# --- Config ---


@pytest.fixture(scope='function', autouse=True)
async def mongo_session():
	if not await connect_mongo():
		pytest.exit(
			f'{TerminalColors.red}'
			f'Failed to connect to MongoDB.'
			f'{TerminalColors.reset}'
		)
	yield
	if not await close_mongo():
		pytest.exit(
			f'{TerminalColors.red}'
			f'Failed to close MongoDB connection.'
			f'{TerminalColors.reset}'
		)


# --- Tests ---


async def test_create_user():
	"""
	Test the user creation functionality.
	It should create a user and return a User object
	with a unique user_id and last_active timestamp.
	"""
	user = await create_user()

	assert user.user_id is not None, 'User ID should not be None'
