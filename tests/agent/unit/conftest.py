"""
Scope in-memory collection fixtures to isolated agent tests.
"""

import pytest

from agent.chat import retrieval as chat_retrieval
from agent.memory import deletion, insertion, retrieval
from database.mongodb.collections import MongoDBCollection
from tests.shared.memory_collection import MemoryCollection


@pytest.fixture
def memory_collection(monkeypatch) -> MemoryCollection:
	"""
	Replace only the collections used by agent memory modules.
	"""
	collection = MemoryCollection([])

	def get_collection(name):
		"""Require the memory collection for each operation."""
		assert name == MongoDBCollection.MEMORIES
		return collection

	for module in (
		deletion,
		insertion,
		retrieval,
		chat_retrieval,
	):
		monkeypatch.setattr(
			module, 'get_collection', get_collection
		)
	return collection
