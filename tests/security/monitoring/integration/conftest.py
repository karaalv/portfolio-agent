"""Isolate bulk security operations in temporary collections."""

from collections.abc import AsyncIterator
from importlib import import_module

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb.collections import (
	MongoDBCollection,
	MongoDBDatabase,
)
from shared.ids import generate_uuid_str
from tests.shared.clients import mongo_client as mongo_client


@pytest_asyncio.fixture(scope='package', loop_scope='package')
async def security_collections(
	mongo_client: AsyncMongoClient,
) -> AsyncIterator[dict[MongoDBCollection, AsyncCollection]]:
	"""Use real collections without touching shared test data."""
	suffix = generate_uuid_str().replace('-', '_')
	database = mongo_client[MongoDBDatabase.ANALYTICS.value]
	collections = {
		kind: database[f'test_security_{kind.value}_{suffix}']
		for kind in (
			MongoDBCollection.USAGE,
			MongoDBCollection.BLOCKED,
		)
	}
	with pytest.MonkeyPatch.context() as monkeypatch:
		for package in ('usage', 'blocked'):
			for operation in (
				'creation',
				'retrieval',
				'update',
				'deletion',
			):
				module = import_module(
					f'security.monitoring.{package}.{operation}'
				)
				monkeypatch.setattr(
					module,
					'get_collection',
					collections.__getitem__,
				)
		try:
			yield collections
		finally:
			for collection in collections.values():
				await collection.drop()


@pytest_asyncio.fixture(autouse=True, loop_scope='package')
async def clean_security_records(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> AsyncIterator[None]:
	"""Reset only the temporary collections between tests."""
	try:
		yield
	finally:
		for collection in security_collections.values():
			await collection.delete_many({})
