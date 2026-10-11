"""Check elapsed spans, early completion and failure cleanup."""

import asyncio

import pytest

from agent.observability import AgentTimer, timing

pytestmark = pytest.mark.unit


def test_explicit_finish_excludes_later_processing(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Stop model timing before subsequent persistence work."""
	clock = iter([10.0, 11.0, 14.0, 20.0])
	monkeypatch.setattr(timing, 'perf_counter', lambda: next(clock))
	timer = AgentTimer()
	with timer.measure('interaction', 'Turn'):
		with timer.measure('openai', 'Round') as response:
			response.finish('response.completed')
			response.finish()
	assert [(r.scope, r.duration_seconds) for r in timer.records] == [
		('openai', 3.0),
		('interaction', 10.0),
	]
	assert timer.records[0].status == 'response.completed'


@pytest.mark.parametrize(
	'exception, status',
	[
		(RuntimeError('failure'), 'failed'),
		(asyncio.CancelledError(), 'cancelled'),
	],
)
def test_errors_finish_spans_and_propagate(
	exception: BaseException,
	status: str,
) -> None:
	"""Retain diagnostics without swallowing task failures."""
	timer = AgentTimer()
	with pytest.raises(type(exception)):
		with timer.measure('tool', 'fetch_context'):
			raise exception
	assert len(timer.records) == 1
	assert timer.records[0].status == status
	assert timer.records[0].duration_seconds >= 0
