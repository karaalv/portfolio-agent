"""Provide a small HTTP app with isolated security state."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.dependencies.auth import ApplicationUserId, IPAccess
from security import lifecycle


@pytest_asyncio.fixture
async def client(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
	"""Exercise dependency injection without external clients."""
	monkeypatch.setenv('JWT_SECRET', 'local-access-test-' * 3)
	monkeypatch.setattr(lifecycle, '_security_client', None)
	monkeypatch.setattr(
		'api.dependencies.auth._checks.enforce_existing_block',
		AsyncMock(),
	)
	await lifecycle.start_security_client()
	app = FastAPI()

	@app.get('/protected')
	async def protected(
		user_id: ApplicationUserId, ip_address: IPAccess
	) -> dict[str, str]:
		"""Reuse the IP dependency to test request caching."""
		return {'user_id': user_id, 'ip': ip_address}

	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(app=app),
			base_url='http://test',
		) as instance:
			yield instance
	finally:
		await lifecycle.stop_security_client()
