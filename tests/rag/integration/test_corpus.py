"""Check corpus uploads and vector index readiness."""

import math

import pytest
from pymongo import AsyncMongoClient

from corpus.helpers import (
	get_corpus_files,
	load_corpus_from_file,
)
from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from rag.config import VECTOR_INDEX_NAME, VECTOR_PATH
from schemas.corpus.item import CorpusItem

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_vector_index_is_queryable(
	mongo_client: AsyncMongoClient,
) -> None:
	"""Require the configured vector index to be queryable."""
	collection = get_collection(MongoDBCollection.CORPUS)
	cursor = await collection.list_search_indexes(
		name=VECTOR_INDEX_NAME,
	)
	async with cursor:
		indexes = await cursor.to_list(length=None)
	assert len(indexes) == 1, (
		'Corpus index missing. Run corpus.bootstrap for testing.'
	)
	index = indexes[0]
	assert index['name'] == VECTOR_INDEX_NAME
	assert index.get('queryable') is True, (
		f'Corpus index is not queryable: {index.get("status")}'
	)
	fields = index['latestDefinition']['fields']
	assert any(
		field.get('type') == 'vector'
		and field.get('path') == VECTOR_PATH
		and field.get('numDimensions') == 3072
		for field in fields
	), 'Corpus index must support the configured vector.'


async def test_corpus_data_is_uploaded(
	mongo_client: AsyncMongoClient,
) -> None:
	"""Require local corpus labels and usable stored vectors."""
	expected_labels: set[str] = set()
	for file in get_corpus_files():
		items = await load_corpus_from_file(file.file_path)
		expected_labels.update(item.label for item in items)
	assert expected_labels, 'The local corpus has no entries.'

	collection = get_collection(MongoDBCollection.CORPUS)
	cursor = collection.find({}, {'_id': 0})
	async with cursor:
		items = [
			CorpusItem.model_validate(document)
			async for document in cursor
		]
	assert items, (
		'Corpus data missing. Run corpus.bootstrap for testing.'
	)
	missing = expected_labels - {item.label for item in items}
	assert not missing, f'Corpus labels not uploaded: {missing}'
	for item in items:
		assert len(item.embedding) == 3072, item.label
		assert all(math.isfinite(v) for v in item.embedding), (
			item.label
		)
		assert any(v != 0 for v in item.embedding), item.label
