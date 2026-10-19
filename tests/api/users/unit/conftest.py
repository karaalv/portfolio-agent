"""Provide isolated HTTP clients for users route unit tests."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI

from api.dependencies.auth.ip import require_ip_access
from api.middleware.origin import OriginMiddleware
from api.routes import users
from security import lifecycle


@pytest.fixture
def user_lookup(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncMock:
	"""Replace the user existence check with a typed mock."""
	lookup = AsyncMock(return_value=True)
	monkeypatch.setattr(users, 'does_user_exist', lookup)
	return lookup


@pytest_asyncio.fixture
async def client(
	monkeypatch: pytest.MonkeyPatch,
	user_lookup: AsyncMock,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Mount the real route and IP gate with isolated clients."""
	monkeypatch.setenv('JWT_SECRET', 'claim-cookie-test-' * 3)
	monkeypatch.setenv('CORS_ORIGINS', 'https://portfolio.test')
	monkeypatch.setenv('COOKIE_DOMAIN', 'api.test')
	monkeypatch.setattr(lifecycle, '_security_client', None)
	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		AsyncMock(),
	)
	await lifecycle.start_security_client()
	app = FastAPI()
	app.include_router(
		users.users_router,
		prefix='/users',
		dependencies=[Depends(require_ip_access)],
	)
	app.add_middleware(
		OriginMiddleware,
		allowed_origins=['https://portfolio.test'],
		protected_prefixes=('/users', '/agent'),
	)
	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(app=app),
			base_url='https://api.test',
			headers={'Origin': 'https://portfolio.test'},
		) as instance:
			yield instance
	finally:
		await lifecycle.stop_security_client()
