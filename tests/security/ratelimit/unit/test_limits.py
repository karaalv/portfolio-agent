"""Check configured bursts, waiting and gradual replenishment."""

import asyncio
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest

from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.ratelimit import RateLimitStore

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'scope, accessor, capacity',
	[
		(ResourceScope.SYSTEM, ResourceAccessor.IP, 500),
		(ResourceScope.SYSTEM, ResourceAccessor.USER, 100),
		(ResourceScope.AGENT_MESSAGE, ResourceAccessor.IP, 1000),
		(ResourceScope.AGENT_MESSAGE, ResourceAccessor.USER, 20),
		(ResourceScope.APPLICATION, ResourceAccessor.IP, 3000),
		(ResourceScope.APPLICATION, ResourceAccessor.USER, 60),
	],
)
async def test_configured_capacity_and_replenishment(
	store: RateLimitStore,
	scope: ResourceScope,
	accessor: ResourceAccessor,
	capacity: int,
) -> None:
	"""Exhaust a burst, then replenish one slot gradually."""
	limiter = await store.get_limiter(scope, accessor, 'caller')
	assert limiter.max_rate == capacity
	assert limiter.time_period == 60
	clock = SimpleNamespace(now=0.0)
	loop = SimpleNamespace(time=lambda: clock.now)
	# Control the limiter's monotonic clock without real waits.
	with patch.object(
		type(limiter), '_loop', new_callable=PropertyMock
	) as loop_property:
		loop_property.return_value = loop
		for _ in range(capacity):
			await limiter.acquire()
		assert not limiter.has_capacity()
		clock.now = 60 / capacity / 2
		assert not limiter.has_capacity()
		clock.now = 60 / capacity + 0.000001
		assert limiter.has_capacity()
		await limiter.acquire()
		assert not limiter.has_capacity()
		clock.now += 60
		assert limiter.has_capacity(capacity)


async def test_exhausted_limiter_waits_for_capacity(
	store: RateLimitStore,
) -> None:
	"""Excess acquisitions wait rather than bypass the limit."""
	limiter = await store.get_limiter(
		ResourceScope.AGENT_MESSAGE, ResourceAccessor.USER, 'a'
	)
	await limiter.acquire(limiter.max_rate)
	waiter = asyncio.create_task(limiter.acquire())
	try:
		await asyncio.sleep(0)
		assert not waiter.done()
	finally:
		waiter.cancel()
		with suppress(asyncio.CancelledError):
			await waiter
