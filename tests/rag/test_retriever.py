"""
This module contains tests for the
retriever functionality as part of
the RAG system.
"""

import time

import pytest

from common.utils import TerminalColors
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)
from rag.query_executor import retrieve_documents_sequential
from rag.schemas import QueryPlan

# --- Constants ---

TEST_QUERY = QueryPlan(
	queries=[
		# "what are your career goals?",
		'what is your favorite programming language?',
		# "what is your greatest strength?"
	]
)

# --- Config ---


@pytest.fixture(scope='function', autouse=True)
async def mongo_session():
	if not await connect_mongo():
		pytest.exit(
			f'{TerminalColors.red}'
			f'Failed to connect to MongoDB.'
			f'{TerminalColors.reset}'
		)
	yield
	if not await close_mongo():
		pytest.exit(
			f'{TerminalColors.red}'
			f'Failed to close MongoDB connection.'
			f'{TerminalColors.reset}'
		)


# --- Tests ---


async def test_retrieve_documents():
	"""
	Test semantic document retrieval.
	"""
	start = time.perf_counter()
	results = await retrieve_documents_sequential(
		user_id='test_user',
		query_plan=TEST_QUERY,
		streaming_context='agent_thinking',
		verbose=True,
	)
	end = time.perf_counter()

	print(
		f'{TerminalColors.yellow}'
		f'Retrieved documents in {end - start:.2f} s'
		f'{TerminalColors.reset}'
	)

	print('--- Results ---')
	print(results)

	assert results is not None, 'Expected non-null results'
