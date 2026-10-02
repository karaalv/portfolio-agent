"""Check RAG planning and orchestration without live services."""

import json
import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from rag import main, query_planner
from schemas.agent.memory import AgentMemory
from schemas.rag.query import QueryPlan


class RagPlanningTests(unittest.IsolatedAsyncioTestCase):
	"""Verify history encoding and orchestration arguments."""

	async def test_planner_serialises_memory(self):
		memory = AgentMemory(
			memory_id='memory',
			user_id='visitor',
			memory_source='user',
			content='Tell me about the portfolio agent.',
		)
		plan = QueryPlan(queries=['portfolio agent'])
		with (
			patch.object(
				query_planner,
				'retrieve_agent_memory',
				AsyncMock(return_value=[memory]),
			),
			patch.object(
				query_planner,
				'text_response',
				AsyncMock(return_value='How was it built?'),
			) as refine,
			patch.object(
				query_planner,
				'structured_response',
				AsyncMock(return_value=plan),
			) as planner,
		):
			result = await query_planner.plan_rag(
				'visitor', 'How was it built?'
			)
		self.assertEqual(result, plan)
		payload = json.loads(refine.await_args.kwargs['user_prompt'])
		self.assertEqual(
			payload['history'][0]['content'], memory.content
		)
		self.assertIsInstance(
			payload['history'][0]['created_at'], str
		)
		self.assertIs(
			planner.await_args.kwargs['response_format'],
			QueryPlan,
		)

	async def test_fetch_context_delegates(self):
		plan = QueryPlan(queries=['backend experience'])
		with (
			patch.object(
				main, 'plan_rag', AsyncMock(return_value=plan)
			) as planner,
			patch.object(
				main,
				'execute_rag',
				AsyncMock(return_value='context'),
			) as executor,
		):
			result = await main.fetch_context(
				'visitor', 'experience', True
			)
		self.assertEqual(result, 'context')
		planner.assert_awaited_once_with(
			'visitor', 'experience', True
		)
		executor.assert_awaited_once_with(plan, 'experience', True)

	def test_query_limit(self):
		with self.assertRaises(ValidationError):
			QueryPlan(queries=['one', 'two', 'three', 'four'])
