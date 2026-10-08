"""Provide isolated stores and a controllable UTC clock."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import pytest_asyncio

from security.ratelimit import RateLimitStore


@pytest.fixture
def utc_clock(
	monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
	"""Control access timestamps without changing loop time."""
	clock = SimpleNamespace(
		now=datetime(2026, 10, 8, tzinfo=UTC)
	)
	monkeypatch.setattr(
		'security.ratelimit.ratelimit_store.'
		'get_utc_datetime_now',
		lambda: clock.now,
	)
	return clock


@pytest_asyncio.fixture
async def store() -> AsyncIterator[RateLimitStore]:
	"""Stop every store's background task after the test."""
	instance = RateLimitStore()
	try:
		yield instance
	finally:
		await instance.stop()
