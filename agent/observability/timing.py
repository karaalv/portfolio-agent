"""Measure turn, tool and model durations with a steady clock."""

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

TimingScope = Literal['interaction', 'tool', 'openai']


@dataclass(frozen=True, slots=True)
class AgentTiming:
	"""One completed measurement, suitable for logging or export."""

	scope: TimingScope
	name: str
	duration_seconds: float
	status: str


class _Measurement:
	"""Finish one span once, even when cleanup runs afterwards."""

	def __init__(
		self,
		records: list[AgentTiming],
		scope: TimingScope,
		name: str,
	) -> None:
		self._records = records
		self._scope: TimingScope = scope
		self._name = name
		self._started_at = perf_counter()
		self._finished = False

	def finish(self, status: str = 'completed') -> None:
		"""Record elapsed seconds without duplicating a span."""
		if self._finished:
			return
		self._records.append(
			AgentTiming(
				scope=self._scope,
				name=self._name,
				duration_seconds=perf_counter() - self._started_at,
				status=status,
			)
		)
		self._finished = True


class AgentTimer:
	"""Own measurements for one turn, including recursive rounds.

	Create a fresh instance per interaction. Concurrent tool
	spans have independent start times. Durations overlap and
	must not be added together to calculate turn latency.
	"""

	def __init__(self) -> None:
		"""Prepare an empty collection without starting a clock."""
		self._records: list[AgentTiming] = []

	@property
	def records(self) -> tuple[AgentTiming, ...]:
		"""Return an immutable snapshot in completion order."""
		return tuple(self._records)

	@contextmanager
	def measure(
		self,
		scope: TimingScope,
		name: str,
	) -> Generator[_Measurement, None, None]:
		"""Record completion, exceptions and task cancellation.

		Call finish explicitly when a stream's terminal event
		arrives, excluding subsequent persistence and cleanup.
		"""
		measurement = _Measurement(self._records, scope, name)
		try:
			yield measurement
		except asyncio.CancelledError:
			measurement.finish('cancelled')
			raise
		except BaseException:
			measurement.finish('failed')
			raise
		else:
			measurement.finish()
