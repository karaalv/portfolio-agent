"""Provide isolated HTTP clients and mocked memory operations."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, HTTPException, Request

from api.dependencies.auth import require_ip_access
from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.routes import agent_memory
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response
from authorisation.jwt.create import create_token
from security import lifecycle


@pytest.fixture
def retrieve_page(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Replace chat retrieval while exercising the real route."""
	mock = AsyncMock(return_value=[])
	monkeypatch.setattr(
		agent_memory, 'retrieve_agent_chat_page', mock
	)
	return mock


@pytest.fixture
def delete_memory(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Replace deletion while retaining access checks."""
	mock = AsyncMock(return_value=0)
	monkeypatch.setattr(
		agent_memory, 'delete_agent_memory', mock
	)
	return mock


@pytest.fixture
def block_check(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Replace persisted block checks with a typed mock."""
	mock = AsyncMock()
	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		mock,
	)
	return mock


@pytest_asyncio.fixture
async def client(
	monkeypatch: pytest.MonkeyPatch,
	retrieve_page: AsyncMock,
	delete_memory: AsyncMock,
	block_check: AsyncMock,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Mount authenticated memory routes without live clients."""
	monkeypatch.setenv('JWT_SECRET', 'memory-route-test-' * 3)
	monkeypatch.setattr(lifecycle, '_security_client', None)
	await lifecycle.start_security_client()
	app = FastAPI()
	app.include_router(
		agent_memory.agent_memory_router,
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
		"""Use the server's HTTP error envelope."""
		return create_http_response(
			request_id=get_request_id(request),
			success=False,
			message=str(exc.detail),
			status_code=exc.status_code,
		)

	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(app=app),
			base_url='https://api.test',
			headers={'Origin': 'https://portfolio.test'},
			cookies={'JWT': create_token('visitor')},
		) as instance:
			yield instance
	finally:
		await lifecycle.stop_security_client()
