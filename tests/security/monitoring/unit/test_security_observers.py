"""Check observer maintenance and UTC scheduling boundaries."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from security.observers.block_observer import BlockObserver
from security.observers.usage_observer import (
	UsageObserver,
	_seconds_until_utc_midnight,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'now, expected',
	[
		(datetime(2026, 10, 8, tzinfo=UTC), 86400),
		(datetime(2026, 10, 8, 23, 59, 30, tzinfo=UTC), 30),
	],
)
def test_next_midnight_is_always_in_the_future(
	now: datetime, expected: int
) -> None:
	"""Sleep to the next midnight, including at midnight."""
	with patch(
		'security.observers.usage_observer.get_utc_datetime_now',
		return_value=now,
	):
		assert _seconds_until_utc_midnight() == expected


async def test_usage_observer_reconciles_and_prunes() -> None:
	"""Run both daily jobs without starting background tasks."""
	with (
		patch(
			'security.observers.usage_observer.'
			'reset_daily_usage',
			new_callable=AsyncMock,
		) as reset,
		patch(
			'security.observers.usage_observer.'
			'prune_inactive_usage',
			new_callable=AsyncMock,
		) as prune,
	):
		await UsageObserver().run_once()
		reset.assert_awaited_once()
		prune.assert_awaited_once()


@pytest.mark.parametrize(
	'observer_type', [UsageObserver, BlockObserver]
)
async def test_observer_start_and_stop_own_one_task(
	observer_type: type[UsageObserver] | type[BlockObserver],
) -> None:
	"""Start once, run at startup and stop without task leaks."""
	observer = observer_type()
	with patch.object(
		observer, 'run_once', new_callable=AsyncMock
	) as maintain:
		try:
			observer.start()
			task = observer._task
			assert task is not None
			observer.start()
			assert observer._task is task
			await asyncio.sleep(0)
			maintain.assert_awaited_once()
		finally:
			await observer.stop()
		assert task.done()
		assert observer._task is None
		await observer.stop()
