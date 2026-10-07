"""Client fixtures imported only by live integration packages."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import dotenv_values
from openai import AsyncOpenAI
from pymongo import AsyncMongoClient

from api.lifecycle import environment
from database.mongodb.config import (
	get_mongo_client,
	start_mongo_client,
	stop_mongo_client,
)
from openai_client.config import (
	get_openai_client,
	start_openai_client,
	stop_openai_client,
)


def load_test_environment(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Load testing settings with scoped restoration."""
	if os.getenv('PORTFOLIO_AGENT_ENV') != 'testing':
		pytest.fail(
			'Live tests require PORTFOLIO_AGENT_ENV=testing.'
		)
	path = Path(__file__).resolve().parents[2] / '.env.testing'
	if not path.is_file():
		pytest.fail(
			'Live tests require a root .env.testing file.'
		)
	for key, value in dotenv_values(path).items():
		if value is not None:
			monkeypatch.setenv(key, value)
	if os.getenv('PORTFOLIO_AGENT_ENV') != 'testing':
		pytest.fail(
			'.env.testing must select the testing environment.'
		)
	monkeypatch.setattr(environment, '_is_env_loaded', False)
	environment.load_environment_variables()


@pytest_asyncio.fixture(scope='package', loop_scope='package')
async def mongo_client() -> AsyncIterator[AsyncMongoClient]:
	"""Share MongoDB across requesting tests in one package."""
	with pytest.MonkeyPatch.context() as monkeypatch:
		load_test_environment(monkeypatch)
		try:
			await start_mongo_client()
			yield get_mongo_client()
		finally:
			await stop_mongo_client()


@pytest_asyncio.fixture(scope='package', loop_scope='package')
async def openai_client() -> AsyncIterator[AsyncOpenAI]:
	"""Share OpenAI across requesting tests in one package."""
	with pytest.MonkeyPatch.context() as monkeypatch:
		load_test_environment(monkeypatch)
		try:
			start_openai_client()
			yield get_openai_client()
		finally:
			await stop_openai_client()
