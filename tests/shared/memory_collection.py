"""In-memory MongoDB doubles for isolated agent CRUD tests."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock


class MemoryCursor:
	"""Apply ordering and offsets to selected test documents."""

	def __init__(self, documents: list[dict]) -> None:
		"""
		Copy selected records for independent cursor operations.
		"""
		self.documents = deepcopy(documents)
		self.offset = 0
		self.count: int | None = None

	def sort(self, fields: list[tuple[str, int]]):
		"""Apply stable compound ordering before pagination."""
		for field, direction in reversed(fields):
			self.documents.sort(
				key=lambda row, field=field: row[field],
				reverse=direction == -1,
			)
		return self

	def skip(self, offset: int):
		"""Advance the cursor past the given record count."""
		self.offset = offset
		return self

	def limit(self, count: int):
		"""Bound the number of returned records."""
		self.count = count
		return self

	async def to_list(self, length=None) -> list[dict]:
		"""
		Return the selected page, optionally bounded by length.
		"""
		rows = self.documents[self.offset :]
		if self.count is not None:
			rows = rows[: self.count]
		return rows if length is None else rows[:length]

	async def __aiter__(self):
		"""Yield records using the configured cursor window."""
		for row in await self.to_list():
			yield row

	async def __aenter__(self):
		"""Expose the cursor inside an async context manager."""
		return self

	async def __aexit__(self, *args):
		"""
		Allow exceptions to propagate from cursor consumption.
		"""
		return False


class MemoryCollection:
	"""
	Record writes and support agent memory query predicates.
	"""

	def __init__(self, documents: list[dict]) -> None:
		"""
		Keep copied records and inspectable async write mocks.
		"""
		self.documents = deepcopy(documents)
		self.queries: list[dict] = []
		self.insert_one = AsyncMock(side_effect=self._insert)
		self.delete_many = AsyncMock(side_effect=self._delete)

	def find(
		self, query: dict, projection: dict
	) -> MemoryCursor:
		"""
		Select records for the supported agent query fields.
		"""
		self.queries.append(deepcopy(query))
		rows = []
		for row in self.documents:
			matches = True
			for field, expected in query.items():
				value = row
				for key in field.split('.'):
					value = value.get(key) if value else None
				if isinstance(expected, dict):
					if '$in' in expected:
						matches &= value in expected['$in']
					elif '$gte' in expected:
						matches &= value >= expected['$gte']
				else:
					matches &= value == expected
			if matches:
				rows.append(row)
		return MemoryCursor(rows)

	async def _insert(self, document: dict) -> None:
		"""Append a copied serialised memory record."""
		self.documents.append(deepcopy(document))

	async def _delete(self, query: dict) -> SimpleNamespace:
		"""
		Remove only records belonging to the requested visitor.
		"""
		before = len(self.documents)
		self.documents = [
			row
			for row in self.documents
			if row['user_id'] != query['user_id']
		]
		return SimpleNamespace(
			deleted_count=before - len(self.documents)
		)
