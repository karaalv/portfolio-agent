"""Translate bounded limiter waits into API transport errors."""

import asyncio

from aiolimiter import AsyncLimiter
from fastapi import HTTPException, WebSocketException, status

from api.config.timeouts import (
	HTTP_RATE_LIMIT_TIMEOUT_SECONDS,
)
from api.config.timeouts import (
	WS_HANDSHAKE_RATE_LIMIT_TIMEOUT_SECONDS as _WS_TIMEOUT,
)


async def acquire_http_rate_limit(
	limiter: AsyncLimiter,
	timeout_seconds: float = HTTP_RATE_LIMIT_TIMEOUT_SECONDS,
) -> None:
	"""Acquire capacity or reject the HTTP request with 429."""
	try:
		async with asyncio.timeout(timeout_seconds):
			await limiter.acquire()
	except TimeoutError as exc:
		raise HTTPException(
			status_code=status.HTTP_429_TOO_MANY_REQUESTS,
			detail='Rate limit exceeded. Try again later.',
		) from exc


async def acquire_ws_rate_limit(
	limiter: AsyncLimiter,
	timeout_seconds: float = _WS_TIMEOUT,
) -> None:
	"""Acquire capacity or raise a WebSocket retry error."""
	try:
		async with asyncio.timeout(timeout_seconds):
			await limiter.acquire()
	except TimeoutError as exc:
		raise WebSocketException(
			code=status.WS_1013_TRY_AGAIN_LATER,
			reason='Rate limit exceeded. Try again later.',
		) from exc
