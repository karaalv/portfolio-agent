"""
This module contains tests for
the agent interface. This is
mainly functional tests and not
logical tests.
"""

import pytest

from agent.main import chat
from agent.memory.main import delete_memory, retrieve_memory
from agent.memory.schemas import AgentMemory
from common.utils import TerminalColors
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)

# --- Constants ---

TEST_DATA = {
	'user_id': 'test_user',
}

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


async def test_chat():
	"""
	Test the chat functionality of the agent.
	It should return a response output item with
	a valid message.
	"""
	response = await chat(
		user_id=TEST_DATA['user_id'],
		input='Hello, who are you?',
		ip='127.0.0.1',
		ua='Mozilla/5.0',
	)

	assert response is not None, 'Response message should not be None'


async def test_memory_retrieval():
	"""
	Test the memory retrieval functionality of the agent.
	It should return the correct memory item for the user.
	"""
	memory: list[AgentMemory] = await retrieve_memory(
		user_id=TEST_DATA['user_id'], to_str=False
	)

	assert memory is not None, 'Memory item should not be None'

	assert memory[0].user_id == TEST_DATA['user_id'], (
		'Memory item user_id should match'
	)


async def test_memory_deletion():
	"""
	Test the memory deletion functionality of the agent.
	It should delete the correct memory item for the user.
	"""
	result = await delete_memory(user_id=TEST_DATA['user_id'])

	assert result is True, 'Memory deletion should be successful'
