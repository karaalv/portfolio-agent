"""Check inactivity pruning and owned cleanup task behaviour."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from schemas.security.ratelimit import (
	ResourceAccessor,
	ResourceScope,
)
from security.ratelimit import RateLimitStore

pytestmark = pytest.mark.unit


async def test_prune_removes_only_inactive_limiters(
	store: RateLimitStore, utc_clock: SimpleNamespace
) -> None:
	"""Keep recent, refreshed and exact-boundary entries."""
	for name in ('stale', 'boundary', 'recent', 'refreshed'):
		await store.get_limiter(
			ResourceScope.APPLICATION,
			ResourceAccessor.USER,
			name,
		)
	records = {
		record.identifier_value: record
		for record in (await store.get_all_limiters()).values()
	}
	records['stale'].last_accessed_at -= timedelta(
		days=3, seconds=1
	)
	records['boundary'].last_accessed_at -= timedelta(days=3)
	records['refreshed'].last_accessed_at -= timedelta(days=4)
	await store.get_limiter(
		ResourceScope.APPLICATION,
		ResourceAccessor.USER,
		'refreshed',
	)
	await store.prune_once()
	remaining = {
		record.identifier_value
		for record in (await store.get_all_limiters()).values()
	}
	assert remaining == {'boundary', 'recent', 'refreshed'}
	assert records['refreshed'].last_accessed_at == utc_clock.now
	await store.prune_once()
	assert len(await store.get_all_limiters()) == 3


async def test_background_cleanup_runs_and_retries(
	utc_clock: SimpleNamespace,
) -> None:
	"""Run scheduled pruning and recover from a failed pass."""
	release = asyncio.Queue[None]()
	intervals: list[int] = []
	finished = asyncio.Event()

	async def controlled_sleep(seconds: int) -> None:
		intervals.append(seconds)
		await release.get()

	with (
		patch(
			'security.ratelimit.ratelimit_store.asyncio',
			wraps=asyncio,
		) as runtime,
		patch(
			'security.ratelimit.ratelimit_store.rich_print'
		) as log,
	):
		runtime.sleep = controlled_sleep
		runtime.CancelledError = asyncio.CancelledError
		store = RateLimitStore()
		try:
			await store.get_limiter(
				ResourceScope.APPLICATION,
				ResourceAccessor.USER,
				'stale',
			)
			utc_clock.now += timedelta(days=4)
			original_prune = store.prune_once
			attempts = 0

			async def prune() -> None:
				nonlocal attempts
				attempts += 1
				if attempts == 1:
					raise RuntimeError('simulated failure')
				await original_prune()
				finished.set()

			store.prune_once = AsyncMock(side_effect=prune)
			await asyncio.sleep(0)
			assert attempts == 0
			assert len(await store.get_all_limiters()) == 1
			release.put_nowait(None)
			release.put_nowait(None)
			await asyncio.wait_for(finished.wait(), timeout=1)
			assert attempts == 2
			assert await store.get_all_limiters() == {}
			assert intervals == [43200, 43200, 43200]
			log.assert_called_once()
		finally:
			await store.stop()


async def test_stop_cancels_cleanup_and_is_repeatable(
	store: RateLimitStore,
) -> None:
	"""Finish the owned task without leaking cancellation."""
	task = store._cleanup_task
	assert task is not None
	await asyncio.sleep(0)
	await store.stop()
	assert task.done()
	assert task.cancelled()
	assert store._cleanup_task is None
	await store.stop()
