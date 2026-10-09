"""Own live clients and temporary endpoint-test collections."""

from collections.abc import AsyncIterator
from importlib import import_module

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, HTTPException, Request
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

from api.dependencies.auth import require_ip_access
from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.routes.agent_memory import agent_memory_router
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response
from authorisation.jwt.create import create_token
from database.mongodb.collections import (
	MongoDBCollection,
	MongoDBDatabase,
)
from security import lifecycle
from shared.ids import generate_uuid_str
from tests.shared.clients import mongo_client as mongo_client


@pytest_asyncio.fixture(scope='package', loop_scope='package')
async def memory_collection(
	mongo_client: AsyncMongoClient,
) -> AsyncIterator[AsyncCollection]:
	"""Run real operations in isolated testing collections."""
	suffix = generate_uuid_str().replace('-', '_')
	collections = {
		MongoDBCollection.MEMORIES: mongo_client[
			MongoDBDatabase.APPLICATION.value
		][f'test_api_memories_{suffix}'],
		MongoDBCollection.BLOCKED: mongo_client[
			MongoDBDatabase.ANALYTICS.value
		][f'test_api_blocks_{suffix}'],
	}
	with pytest.MonkeyPatch.context() as monkeypatch:
		for module_name in (
			'agent.chat.retrieval',
			'agent.memory.insertion',
			'agent.memory.deletion',
			'security.monitoring.blocked.retrieval',
		):
			monkeypatch.setattr(
				import_module(module_name),
				'get_collection',
				collections.__getitem__,
			)
		monkeypatch.setattr(lifecycle, '_security_client', None)
		await lifecycle.start_security_client()
		try:
			yield collections[MongoDBCollection.MEMORIES]
		finally:
			try:
				await lifecycle.stop_security_client()
			finally:
				for collection in collections.values():
					await collection.drop()


@pytest_asyncio.fixture(autouse=True, loop_scope='package')
async def clean_memories(
	memory_collection: AsyncCollection,
) -> AsyncIterator[None]:
	"""Remove only this package's temporary records per test."""
	try:
		yield
	finally:
		await memory_collection.delete_many({})


@pytest.fixture
def user_id() -> str:
	"""Allocate an identity unique to this endpoint test."""
	return generate_uuid_str()


@pytest.fixture
def other_user_id() -> str:
	"""Allocate an independent owner for isolation checks."""
	return generate_uuid_str()


@pytest_asyncio.fixture(loop_scope='package')
async def client(
	memory_collection: AsyncCollection,
	user_id: str,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Use real access checks and memory operations over HTTP."""
	app = FastAPI()
	app.include_router(
		agent_memory_router,
		prefix='/agent-memory',
		dependencies=[Depends(require_ip_access)],
	)
	app.add_middleware(
		OriginMiddleware,
		allowed_origins=['https://portfolio.test'],
		protected_prefixes=('/agent-memory',),
	)
	app.add_middleware(RequestIdMiddleware)

	@app.exception_handler(HTTPException)
	async def handle_http_error(request: Request, exc):
		"""Match the server's error response envelope."""
		return create_http_response(
			request_id=get_request_id(request),
			success=False,
			message=str(exc.detail),
			status_code=exc.status_code,
		)

	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://api.test',
		headers={'Origin': 'https://portfolio.test'},
		cookies={'JWT': create_token(user_id)},
	) as instance:
		yield instance
