"""Check retrieval, identity isolation and access metadata."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.ratelimit import RateLimitStore

pytestmark = pytest.mark.unit


async def test_concurrent_lookups_share_one_limiter(
	store: RateLimitStore,
) -> None:
	"""Concurrent lookups must preserve one shared allowance."""
	limiters = await asyncio.gather(
		*(
			store.get_limiter(
				ResourceScope.AGENT_MESSAGE,
				ResourceAccessor.USER,
				'visitor',
			)
			for _ in range(50)
		)
	)
	assert all(limiter is limiters[0] for limiter in limiters)
	assert len(await store.get_all_limiters()) == 1


async def test_identifiers_scopes_and_accessors_are_isolated(
	store: RateLimitStore,
) -> None:
	"""Give each distinct key its own limiter and unique ID."""
	identities = [
		(ResourceScope.APPLICATION, ResourceAccessor.USER, 'a'),
		(ResourceScope.APPLICATION, ResourceAccessor.USER, 'b'),
		(
			ResourceScope.AGENT_MESSAGE,
			ResourceAccessor.USER,
			'a',
		),
		(ResourceScope.APPLICATION, ResourceAccessor.IP, 'a'),
	]
	limiters = [
		await store.get_limiter(*identity)
		for identity in identities
	]
	assert len({id(limiter) for limiter in limiters}) == 4
	records = (await store.get_all_limiters()).values()
	ids = {record.limiter_id for record in records}
	assert len(ids) == 4
	assert all(UUID(value).version == 4 for value in ids)


async def test_lookup_refreshes_access_time(
	store: RateLimitStore, utc_clock: SimpleNamespace
) -> None:
	"""Refresh timestamps while preserving limiter identity."""
	first = await store.get_limiter(
		ResourceScope.APPLICATION, ResourceAccessor.USER, 'a'
	)
	record = next(
		iter((await store.get_all_limiters()).values())
	)
	assert record.last_accessed_at == utc_clock.now
	utc_clock.now += timedelta(hours=1)
	second = await store.get_limiter(
		ResourceScope.APPLICATION, ResourceAccessor.USER, 'a'
	)
	assert second is first
	assert record.last_accessed_at == utc_clock.now
	assert record.last_accessed_at.utcoffset() == timedelta(0)


async def test_stores_have_independent_allowances(
	store: RateLimitStore,
) -> None:
	"""A second app's store must not share consumed capacity."""
	other = RateLimitStore()
	try:
		first = await store.get_limiter(
			ResourceScope.AGENT_MESSAGE,
			ResourceAccessor.USER,
			'a',
		)
		second = await other.get_limiter(
			ResourceScope.AGENT_MESSAGE,
			ResourceAccessor.USER,
			'a',
		)
		await first.acquire(first.max_rate)
		assert second is not first
		assert not first.has_capacity()
		assert second.has_capacity(second.max_rate)
	finally:
		await other.stop()
