"""Provide isolated HTTP and WebSocket route clients."""

from collections.abc import (
	AsyncGenerator,
	AsyncIterator,
	Iterator,
)
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.websocket.helpers.exception_capture import (
	handle_connection_exception,
)
from exceptions.websocket import WebSocketConnectionException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from security import lifecycle
from shared.time import get_utc_datetime_now


@pytest.fixture
def ws_client(
	monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
	"""Mount the chat route with real local socket tracking."""
	import api.websocket.lifecycle as websocket_lifecycle
	from api import websocket
	from api.dependencies.auth.ip import require_ws_ip_access
	from api.routes import agent
	from api.websocket.helpers import access
	from security.monitoring.blocked import enforcement

	def block_record(
		entity: BlockedEntity,
		entity_id: str,
		reason: str,
	) -> BlockedRecord:
		"""Return a persisted block without using live MongoDB."""
		now = get_utc_datetime_now()
		return BlockedRecord(
			entity=entity,
			entity_id=entity_id,
			reason=reason,
			blocked_at=now,
			blocked_until=now + timedelta(days=1),
		)

	monkeypatch.setattr(
		enforcement,
		'create_block',
		AsyncMock(side_effect=block_record),
	)

	monkeypatch.setenv('JWT_SECRET', 'agent-route-test-' * 3)
	monkeypatch.setattr(
		websocket_lifecycle, '_websocket_registry', None
	)
	monkeypatch.setattr(lifecycle, '_security_client', None)
	monkeypatch.setattr(
		access,
		'create_user',
		AsyncMock(return_value=SimpleNamespace(user_id='visitor')),
	)
	monkeypatch.setattr(
		access, 'create_usage_statistics', AsyncMock()
	)
	monkeypatch.setattr(
		access,
		'require_application_access',
		AsyncMock(side_effect=lambda user_id: user_id),
	)
	monkeypatch.setattr(agent, 'agent_chat', AsyncMock())

	@asynccontextmanager
	async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
		"""Keep registry and limiter tasks on the serving loop."""
		await lifecycle.start_security_client()
		await websocket.start_websocket_registry()
		try:
			yield
		finally:
			await websocket.stop_websocket_registry()
			await lifecycle.stop_security_client()

	async def ip_access() -> str:
		"""Isolate socket routing from persisted IP checks."""
		return '127.0.0.1'

	app = FastAPI(lifespan=lifespan)
	app.add_exception_handler(
		WebSocketConnectionException, handle_connection_exception
	)
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	app.include_router(agent.agent_router, prefix='/agent')
	app.dependency_overrides[require_ws_ip_access] = ip_access
	with TestClient(app) as instance:
		yield instance


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
