"""Check bounded acquisition and transport-specific errors."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from aiolimiter import AsyncLimiter
from fastapi import HTTPException, WebSocketException

from api.utils.ratelimit import (
	acquire_http_rate_limit,
	acquire_ws_rate_limit,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'helper, exception, code',
	[
		(acquire_http_rate_limit, HTTPException, 429),
		(acquire_ws_rate_limit, WebSocketException, 1013),
	],
)
async def test_capacity_then_timeout(
	helper: Callable[..., Coroutine[Any, Any, None]],
	exception: type[HTTPException] | type[WebSocketException],
	code: int,
) -> None:
	"""Consume capacity once, then reject the bounded wait."""
	limiter = AsyncLimiter(1, 3600)
	await helper(limiter, timeout_seconds=0.001)
	with pytest.raises(exception) as error:
		await helper(limiter, timeout_seconds=0.001)
	if isinstance(error.value, HTTPException):
		assert error.value.status_code == code
	else:
		assert error.value.code == code


@pytest.mark.parametrize(
	'helper', [acquire_http_rate_limit, acquire_ws_rate_limit]
)
async def test_cancellation_is_not_a_rate_error(
	helper: Callable[..., Coroutine[Any, Any, None]],
) -> None:
	"""Propagate shutdown cancellation instead of 429 or 1013."""
	limiter = AsyncLimiter(1, 3600)
	await limiter.acquire()
	task = asyncio.create_task(
		helper(limiter, timeout_seconds=10)
	)
	await asyncio.sleep(0)
	task.cancel()
	with pytest.raises(asyncio.CancelledError):
		await task
