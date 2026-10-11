"""Verify caption ordering and connection-scoped RAG delivery."""

from unittest.mock import AsyncMock

import pytest

from agent.tools import context, dispatch
from rag import main
from schemas.agent.streaming.stream_manager import (
	StreamManagerFunctionCall,
)
from schemas.rag.query import QueryPlan

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('connection_id', ['socket', None])
async def test_captions_are_sent_between_planning_and_execution(
	monkeypatch: pytest.MonkeyPatch,
	connection_id: str | None,
) -> None:
	"""Send the planner's captions before running its queries."""
	plan = QueryPlan(
		queries=['education'],
		agent_thinking_captions=["Checking Alvin's education"],
	)
	order: list[str] = []

	async def planner(*args) -> QueryPlan:
		"""Return deterministic queries and matching captions."""
		order.append('plan')
		return plan

	async def send(user_id, connection, response) -> None:
		"""Check that only the requesting connection is targeted."""
		order.append('captions')
		assert user_id == 'visitor'
		assert connection == connection_id
		assert response.type == 'agent_thinking_captions'
		assert response.payload == plan.agent_thinking_captions

	async def execute(received_plan, user_input, verbose) -> str:
		"""Execute the original plan after caption delivery."""
		order.append('execute')
		assert received_plan is plan
		return 'Grounded context'

	monkeypatch.setattr(main, 'plan_rag', planner)
	monkeypatch.setattr(main, 'send_agent_ws_response', send)
	monkeypatch.setattr(main, 'execute_rag', execute)
	assert (
		await main.fetch_context(
			'visitor', 'education', connection_id=connection_id
		)
		== 'Grounded context'
	)
	assert order == ['plan', 'captions', 'execute']


async def test_connection_flows_through_tool_dispatch(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Keep socket targeting as application-owned tool context."""
	rag = AsyncMock(return_value='Grounded context')
	monkeypatch.setattr(context, 'retrieve_context', rag)
	call = StreamManagerFunctionCall(
		call_id='call',
		tool_name='fetch_context',
		tool_args='{"user_input":"education"}',
	)
	results = await dispatch.run_function_calls(
		'visitor', {'call': call}, connection_id='socket'
	)
	rag.assert_awaited_once_with(
		user_id='visitor',
		user_input='education',
		verbose=False,
		connection_id='socket',
	)
	assert results == [
		{
			'type': 'function_call_output',
			'call_id': 'call',
			'output': 'Grounded context',
		}
	]
