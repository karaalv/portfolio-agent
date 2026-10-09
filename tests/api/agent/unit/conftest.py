"""Provide an HTTP client scaffold for future agent routes."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware
from security import lifecycle


@pytest_asyncio.fixture
async def client(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Mount agent routes when a test requests the client."""
	from api.routes.agent import agent_router

	monkeypatch.setenv('JWT_SECRET', 'agent-route-test-' * 3)
	monkeypatch.setattr(lifecycle, '_security_client', None)
	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		AsyncMock(),
	)
	await lifecycle.start_security_client()
	app = FastAPI()
	app.include_router(agent_router, prefix='/agent')
	app.add_middleware(
		OriginMiddleware,
		allowed_origins=['https://portfolio.test'],
		protected_prefixes=('/agent',),
	)
	app.add_middleware(RequestIdMiddleware)
	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(app=app),
			base_url='https://api.test',
			headers={'Origin': 'https://portfolio.test'},
		) as instance:
			yield instance
	finally:
		await lifecycle.stop_security_client()
