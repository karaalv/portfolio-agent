"""Create missing corpus resources in the target environment."""

import asyncio

from api.lifecycle.environment import load_environment_variables
from corpus.push_corpus import push_corpus
from corpus.push_index import corpus_index_exists, push_index
from database.mongodb.collections import MongoDBCollection
from database.mongodb.config import (
	is_mongo_connected,
	start_mongo_client,
	stop_mongo_client,
)
from database.mongodb.main import get_collection
from openai_client.config import (
	start_openai_client,
	stop_openai_client,
)
from shared.logging import LogStyle, rich_print


async def main() -> None:
	"""Inspect index and data, then create missing resources.

	Existing data is left intact. This checks for any document,
	not whether every local corpus file has been uploaded.
	"""
	try:
		load_environment_variables()
		await start_mongo_client()
		while not await is_mongo_connected():
			await asyncio.sleep(1)

		index_exists = await corpus_index_exists()
		collection = get_collection(MongoDBCollection.CORPUS)
		data_exists = (
			await collection.find_one({}, {'_id': 1}) is not None
		)

		if index_exists:
			rich_print(
				'Corpus index already exists.', LogStyle.INFO
			)
		else:
			await push_index()

		if data_exists:
			rich_print(
				'Corpus data already exists.', LogStyle.INFO
			)
		else:
			start_openai_client()
			await push_corpus()

		rich_print(
			'Corpus bootstrap complete.', LogStyle.SUCCESS
		)
	finally:
		try:
			await stop_openai_client()
		finally:
			await stop_mongo_client()


if __name__ == '__main__':
	asyncio.run(main())
