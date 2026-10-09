"""Check process-local store ownership and cleanup shutdown."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from exceptions.security import SecurityServiceException
from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security import lifecycle
from security.ratelimit import RateLimitStore

pytestmark = pytest.mark.unit


@pytest_asyncio.fixture(autouse=True)
async def isolated_client(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[None]:
	"""Restore module state and stop every owned test client."""
	monkeypatch.setattr(lifecycle, '_security_client', None)
	try:
		yield
	finally:
		await lifecycle.stop_security_client()


async def test_start_stop_manage_one_store() -> None:
	"""Own one store and finish its task on shutdown."""
	await lifecycle.start_security_client()
	store = lifecycle.get_security_client()
	task = store._cleanup_task
	assert task is not None
	await lifecycle.start_security_client()
	assert lifecycle.get_security_client() is store
	limiter = await lifecycle.get_limiter(
		ResourceScope.APPLICATION,
		ResourceAccessor.USER,
		'visitor',
	)
	assert limiter is await store.get_limiter(
		ResourceScope.APPLICATION,
		ResourceAccessor.USER,
		'visitor',
	)
	await lifecycle.stop_security_client()
	assert task.done()
	with pytest.raises(SecurityServiceException):
		lifecycle.get_security_client()
	await lifecycle.stop_security_client()


async def test_missing_client_cannot_provide_allowances() -> (
	None
):
	"""Require startup before using the forwarding helper."""
	with pytest.raises(SecurityServiceException):
		await lifecycle.get_limiter(
			ResourceScope.APPLICATION,
			ResourceAccessor.IP,
			'127.0.0.1',
		)


async def test_set_client_installs_an_existing_store() -> None:
	"""Use an injected store and stop its owned cleanup task."""
	store = RateLimitStore()
	lifecycle.set_security_client(store)
	assert lifecycle.get_security_client() is store
	await lifecycle.stop_security_client()
	assert store._cleanup_task is None
