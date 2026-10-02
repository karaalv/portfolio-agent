"""Check user-scoped memory windows and pagination boundaries."""

from datetime import UTC, datetime

import pytest

from agent.memory import retrieval
from database.mongodb.collections import MongoDBCollection


class _Cursor:
	"""Apply cursor operations to test records without MongoDB."""

	def __init__(self, documents):
		self.documents = documents
		self.offset = 0
		self.page_size = None

	def sort(self, fields):
		assert fields == [('created_at', -1), ('_id', -1)]
		self.documents.sort(
			key=lambda document: (
				document['created_at'],
				document['_id'],
			),
			reverse=True,
		)
		return self

	def skip(self, offset):
		self.offset = offset
		return self

	def limit(self, page_size):
		self.page_size = page_size
		return self

	async def __aiter__(self):
		documents = self.documents[self.offset :]
		if self.page_size is not None:
			documents = documents[: self.page_size]
		for document in documents:
			yield document


async def test_pages_cover_only_the_users_history(monkeypatch):
	"""Return disjoint chronological pages, including tied dates."""
	documents = [
		{
			'_id': index,
			'memory_id': f'memory-{index}',
			'user_id': 'visitor',
			'memory_source': 'user',
			'created_at': datetime(2026, 10, 2, tzinfo=UTC),
			'content': f'Message {index}',
		}
		for index in range(5)
	]
	documents.append({**documents[0], 'user_id': 'other'})

	class Collection:
		def find(self, query, projection):
			assert query == {'user_id': 'visitor'}
			assert projection == {'_id': 0}
			return _Cursor(
				[
					document
					for document in documents
					if document['user_id'] == query['user_id']
				]
			)

	def get_collection(collection):
		assert collection == MongoDBCollection.MEMORIES
		return Collection()

	monkeypatch.setattr(retrieval, 'get_collection', get_collection)
	monkeypatch.setattr(retrieval, 'AGENT_MEMORY_PAGE_SIZE', 2)

	expected = ([3, 4], [1, 2], [0], [])
	for offset, indices in zip((0, 2, 4, 5), expected, strict=True):
		page = await retrieval.retrieve_agent_memory_page(
			'visitor', offset
		)
		assert [memory.memory_id for memory in page] == [
			f'memory-{index}' for index in indices
		]

	recent = await retrieval.retrieve_agent_memory('visitor', 2)
	assert [memory.memory_id for memory in recent] == [
		'memory-3',
		'memory-4',
	]


async def test_negative_offset_is_rejected_before_query(monkeypatch):
	"""Reject invalid offsets without accessing the database."""

	def unexpected_query(collection):
		raise AssertionError('The database should not be accessed.')

	monkeypatch.setattr(retrieval, 'get_collection', unexpected_query)
	with pytest.raises(ValueError, match='offset'):
		await retrieval.retrieve_agent_memory_page('visitor', -1)
