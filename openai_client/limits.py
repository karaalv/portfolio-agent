"""Limit concurrent and per-minute OpenAI requests."""

from asyncio import AbstractEventLoop, Semaphore, get_running_loop
from functools import lru_cache
from os import getenv
from typing import NamedTuple

from aiolimiter import AsyncLimiter


class _OpenAILimits(NamedTuple):
	"""Limiters shared by calls on one event loop."""

	semaphore: Semaphore
	responses: AsyncLimiter
	embeddings: AsyncLimiter


def _positive_int_env(name: str, default: int) -> int:
	"""Read a positive integer limit from the environment."""
	value = getenv(name, str(default))
	try:
		limit = int(value)
	except ValueError as exc:
		raise ValueError(
			f'{name} must be a positive integer.'
		) from exc
	if limit < 1:
		raise ValueError(f'{name} must be a positive integer.')
	return limit


@lru_cache(maxsize=16)
def _limits_for_loop(loop: AbstractEventLoop) -> _OpenAILimits:
	"""Create one set of limits for each active event loop."""
	return _OpenAILimits(
		semaphore=Semaphore(
			_positive_int_env('OPENAI_MAX_CONCURRENT_REQUESTS', 50)
		),
		responses=AsyncLimiter(
			_positive_int_env('OPENAI_RPM_RESPONSES', 600), 60
		),
		embeddings=AsyncLimiter(
			_positive_int_env('OPENAI_RPM_EMBEDDINGS', 1200), 60
		),
	)


def get_openai_semaphore() -> Semaphore:
	"""Return the concurrency limit for the current event loop."""
	return _limits_for_loop(get_running_loop()).semaphore


def get_openai_response_limiter() -> AsyncLimiter:
	"""Return the response request limiter for this event loop."""
	return _limits_for_loop(get_running_loop()).responses


def get_openai_embedding_limiter() -> AsyncLimiter:
	"""Return the embedding request limiter for this event loop."""
	return _limits_for_loop(get_running_loop()).embeddings

def get_openai_response_timeout() -> int:
	"""Return the response request timeout for this event loop."""
	return _positive_int_env('OPENAI_RESPONSE_TIMEOUT', 120)