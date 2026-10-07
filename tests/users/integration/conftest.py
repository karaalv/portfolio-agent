"""Client setup and cleanup for users integration tests."""

from collections.abc import AsyncIterator

import pytest_asyncio
from pymongo import AsyncMongoClient

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from tests.shared.clients import mongo_client as mongo_client


@pytest_asyncio.fixture(loop_scope='package')
async def user_ids(
	mongo_client: AsyncMongoClient,
) -> AsyncIterator[list[str]]:
	"""Track and clean up only test-created user records."""
	ids: list[str] = []
	try:
		yield ids
	finally:
		if ids:
			collection = get_collection(MongoDBCollection.USERS)
			await collection.delete_many(
				{'user_id': {'$in': ids}}
			)
