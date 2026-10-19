"""Check a live MongoDB connection and a collection read."""

import pytest
from pymongo import AsyncMongoClient

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from database.mongodb.config import is_mongo_connected
from shared.ids import generate_uuid_str

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_mongo_is_connected(
	mongo_client: AsyncMongoClient,
) -> None:
	"""Require a successful ping, not just a boolean result."""
	assert await is_mongo_connected() is True


async def test_mongo_collection_read(
	mongo_client: AsyncMongoClient,
) -> None:
	"""Read a collection using a unique identity query."""
	collection = get_collection(MongoDBCollection.USERS)
	result = await collection.find_one(
		{'user_id': generate_uuid_str()}, {'_id': 1}
	)
	assert result is None
