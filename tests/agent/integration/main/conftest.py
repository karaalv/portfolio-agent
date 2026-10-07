"""Observe live agent streams without replacing model results."""

from contextlib import aclosing
from copy import deepcopy

import pytest

from agent import main
from agent.input_items import response_item_to_input_item
from tests.schemas.agent import AgentTrace


@pytest.fixture
def agent_trace(monkeypatch) -> AgentTrace:
	"""Capture the requests and events used by the agent loop."""
	trace = AgentTrace()
	original = main.stream_agent_response

	async def observe(**kwargs):
		"""
		Record real responses and yield every event unchanged.
		"""
		trace.inputs.append(deepcopy(kwargs['input']))
		assert trace.closed == len(trace.inputs) - 1
		try:
			async with aclosing(original(**kwargs)) as events:
				async for event in events:
					if (
						event.type
						== 'response.output_text.delta'
					):
						trace.deltas.append(event.delta)
					elif event.type == 'response.completed':
						trace.outputs.append(
							[
								response_item_to_input_item(item)
								for item in event.response.output
							]
						)
					elif event.type in {
						'error',
						'response.failed',
						'response.incomplete',
					}:
						pytest.fail(
							f'Agent stream failed: {event.type}'
						)
					yield event
		finally:
			trace.closed += 1

	monkeypatch.setattr(main, 'stream_agent_response', observe)
	return trace
