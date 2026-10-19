"""Share agent clients and clean up test-owned identities."""

from collections.abc import AsyncIterator

import pytest_asyncio
from pymongo import AsyncMongoClient

from agent.memory.deletion import delete_agent_memory
from shared.ids import generate_uuid_str
from tests.shared.clients import mongo_client as mongo_client
from tests.shared.clients import openai_client as openai_client
from users.deletion import delete_user


@pytest_asyncio.fixture(loop_scope='package')
async def user_id(mongo_client: AsyncMongoClient):
	"""
	Allocate a visitor ID and remove its records after the test.
	"""
	identity = generate_uuid_str()
	try:
		yield identity
	finally:
		try:
			await delete_agent_memory(identity)
		finally:
			await delete_user(identity)


@pytest_asyncio.fixture(loop_scope='package')
async def other_user_id(
	mongo_client: AsyncMongoClient,
) -> AsyncIterator[str]:
	"""Allocate a separate identity for ownership isolation."""
	identity = generate_uuid_str()
	try:
		yield identity
	finally:
		try:
			await delete_agent_memory(identity)
		finally:
			await delete_user(identity)
