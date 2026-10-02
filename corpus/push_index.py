"""Create the corpus vector index and wait for queryability."""

import asyncio

from pymongo.operations import SearchIndexModel

from api.lifecycle.environment import load_environment_variables
from database.mongodb.collections import MongoDBCollection
from database.mongodb.config import (
	is_mongo_connected,
	start_mongo_client,
	stop_mongo_client,
)
from database.mongodb.main import get_collection
from shared.logging import LogStyle, rich_print


async def main() -> None:
	"""Create the vector index and close MongoDB on exit."""
	try:
		await _startup()
		await _push_index()
	finally:
		await _shutdown()


async def _startup() -> None:
	"""Load the environment and wait for MongoDB connectivity."""
	load_environment_variables()
	await start_mongo_client()
	while not await is_mongo_connected():
		await asyncio.sleep(1)


async def _shutdown() -> None:
	"""Close the process-local MongoDB client."""
	await stop_mongo_client()


async def _push_index() -> None:
	"""Create the vector index and poll its queryable flag."""
	index_name = 'corpus_vector_index'
	collection = get_collection(MongoDBCollection.CORPUS)
	vector_index = SearchIndexModel(
		name=index_name,
		type='vectorSearch',
		definition={
			'fields': [
				{
					'type': 'vector',
					'path': 'embedding',
					'numDimensions': 3072,
					'similarity': 'cosine',
				}
			],
		},
	)

	rich_print('Creating vector search index...', LogStyle.INFO)
	await collection.create_search_index(vector_index)

	while True:
		cursor = await collection.list_search_indexes(
			name=index_name,
		)
		async for index in cursor:
			if index.get('status') == 'FAILED':
				raise RuntimeError(
					f'Index {index_name!r} build failed.'
				)
			if index.get('queryable') is True:
				rich_print(
					'Vector search index is queryable.',
					LogStyle.SUCCESS,
				)
				return
		await asyncio.sleep(5)


if __name__ == '__main__':
	asyncio.run(main())
