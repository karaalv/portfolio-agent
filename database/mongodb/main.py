"""Main module for MongoDB operations."""

from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb.collections import (
	MONGODB_COLLECTION_TO_DATABASE,
	MongoDBCollection,
)
from database.mongodb.config import get_mongo_client
from exceptions.mongodb import MongoDBException

# --- Resource Resolvers ---


def get_collection(collection: MongoDBCollection) -> AsyncCollection:
	"""
	Retrieves a collection from
	MongoDB, resolves the database
	during the process.

	Args:
		collection (MongoDBCollection): The
		collection enumeration member to retrieve.

	Returns:
		AsyncCollection: The collection object.
	"""
	client = get_mongo_client()

	if collection not in MONGODB_COLLECTION_TO_DATABASE:
		raise MongoDBException(
			message=(
				f'Collection "{collection.value}" is not '
				'defined in the collection map.'
			),
			module='database.mongodb.main',
			operation='get_collection',
		)

	db = MONGODB_COLLECTION_TO_DATABASE[collection]
	return client[db.value][collection.value]
