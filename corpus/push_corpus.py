"""Embed and upload corpus documents to MongoDB file by file."""

import asyncio

from api.lifecycle.environment import load_environment_variables
from corpus.helpers import (
	get_corpus_files,
	load_corpus_from_file,
)
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
from schemas.corpus.item import CorpusItem
from shared.logging import LogStyle, rich_print


async def main() -> None:
	"""Upload each corpus file and close clients on exit."""
	try:
		await _startup()
		await push_corpus()
	finally:
		await _shutdown()


async def push_corpus() -> None:
	"""Embed and upload files using already-started clients."""
	rich_print('Starting corpus upload...', LogStyle.INFO)
	for file in get_corpus_files():
		rich_print(
			f'Processing file: {file.file_path}',
			LogStyle.INFO,
		)
		items = await load_corpus_from_file(
			file.file_path,
			embeddings=True,
		)
		inserted_count = await insert_corpus_items(items)
		rich_print(
			f'Inserted {inserted_count} items '
			f'from {file.label}.',
			LogStyle.SUCCESS,
		)
	rich_print('Corpus upload complete.', LogStyle.SUCCESS)


async def _startup() -> None:
	"""Load the environment and start MongoDB and OpenAI."""
	load_environment_variables()
	await start_mongo_client()
	while not await is_mongo_connected():
		await asyncio.sleep(1)
	start_openai_client()


async def _shutdown() -> None:
	"""Attempt to close both process-local clients."""
	try:
		await stop_openai_client()
	finally:
		await stop_mongo_client()


async def insert_corpus_items(items: list[CorpusItem]) -> int:
	"""Insert one file's items and return the inserted count.

	Skip empty files. Existing records are retained, so repeat
	uploads append new records with fresh item IDs.
	"""
	if not items:
		return 0
	collection = get_collection(MongoDBCollection.CORPUS)
	result = await collection.insert_many(
		[item.model_dump() for item in items],
	)
	return len(result.inserted_ids)


if __name__ == '__main__':
	asyncio.run(main())
