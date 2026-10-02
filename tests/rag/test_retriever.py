"""Check parallel retrieval and refinement without services."""

import asyncio
import builtins
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from rag import query_executor
from schemas.corpus.item import CorpusItem
from schemas.rag.query import QueryPlan


def _item(item_id: str) -> CorpusItem:
	"""Create a corpus entry for retrieval checks."""
	return CorpusItem(
		item_id=item_id,
		label=f'topic_{item_id}',
		header='Retrieving experience',
		embedding=[],
		context='Backend engineering',
		document='Alvin built a portfolio agent.',
	)


class RagExecutionTests(unittest.IsolatedAsyncioTestCase):
	"""Verify concurrent tasks, evidence merging and failures."""

	async def test_parallel_order_and_deduplication(self):
		both_started = asyncio.Event()
		started = []

		async def retrieve(query, verbose):
			started.append(query)
			if len(started) == 2:
				both_started.set()
			await asyncio.wait_for(both_started.wait(), 1)
			if query == 'first':
				await asyncio.sleep(0)
			return [_item(query), _item('shared')]

		with (
			patch.object(
				query_executor, '_retrieve_query', retrieve
			),
			patch.object(
				query_executor,
				'_refine_context',
				AsyncMock(return_value='grounded context'),
			) as refine,
		):
			result = await query_executor.execute_rag(
				QueryPlan(queries=['first', 'second']), 'request'
			)
		self.assertEqual(result, 'grounded context')
		items = refine.await_args.args[1]
		self.assertEqual(
			[item.item_id for item in items],
			['first', 'shared', 'second'],
		)

	async def test_failed_query_cancels_sibling(self):
		started = asyncio.Event()
		cancelled = asyncio.Event()

		async def retrieve(query, verbose):
			if query == 'fail':
				await started.wait()
				raise RuntimeError('retrieval failed')
			started.set()
			try:
				await asyncio.Event().wait()
			finally:
				cancelled.set()

		with patch.object(
			query_executor, '_retrieve_query', retrieve
		):
			with self.assertRaises(builtins.ExceptionGroup):
				await query_executor.execute_rag(
					QueryPlan(queries=['fail', 'wait']),
					'request',
				)
		self.assertTrue(cancelled.is_set())

	async def test_empty_results_skip_refinement(self):
		with (
			patch.object(
				query_executor,
				'_retrieve_query',
				AsyncMock(return_value=[]),
			) as retrieve,
			patch.object(
				query_executor, '_refine_context', AsyncMock()
			) as refine,
		):
			await query_executor.execute_rag(
				QueryPlan(queries=[]), 'request'
			)
			retrieve.assert_not_awaited()
			result = await query_executor.execute_rag(
				QueryPlan(queries=['missing']), 'request'
			)
			self.assertIn('No relevant', result)
			refine.assert_not_awaited()

	async def test_projected_documents_validate(self):
		document = _item('one').model_dump(exclude={'embedding'})
		cursor = MagicMock()
		cursor.to_list = AsyncMock(return_value=[document])
		cursor.__aenter__ = AsyncMock(return_value=cursor)
		cursor.__aexit__ = AsyncMock(return_value=False)
		collection = MagicMock()
		collection.aggregate = AsyncMock(return_value=cursor)
		with (
			patch.object(
				query_executor,
				'get_collection',
				return_value=collection,
			),
			patch.object(
				query_executor,
				'get_embedding',
				AsyncMock(return_value=[0.5]),
			),
		):
			items = await query_executor._retrieve_query('query')
		self.assertEqual(items, [_item('one')])
		pipeline = collection.aggregate.await_args.args[0]
		self.assertEqual(
			pipeline[0]['$vectorSearch']['queryVector'], [0.5]
		)
		cursor.__aexit__.assert_awaited_once()

	async def test_refinement_preserves_source_labels(self):
		with patch.object(
			query_executor,
			'text_response',
			AsyncMock(return_value='context'),
		) as response:
			await query_executor._refine_context(
				'question', [_item('one')]
			)
		payload = json.loads(
			response.await_args.kwargs['user_prompt']
		)
		self.assertEqual(payload['user_input'], 'question')
		self.assertEqual(
			payload['entries'][0]['label'], 'topic_one'
		)
