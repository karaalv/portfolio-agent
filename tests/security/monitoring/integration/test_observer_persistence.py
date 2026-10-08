"""Exercise observer maintenance against real MongoDB data."""

from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb.collections import MongoDBCollection
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from schemas.security.monitoring.usage import UsageEntity
from security.monitoring.blocked.enforcement import (
	enforce_existing_block,
)
from security.monitoring.blocked.retrieval import retrieve_block
from security.monitoring.usage.creation import (
	create_usage_statistics,
)
from security.monitoring.usage.retrieval import (
	retrieve_usage_statistics,
)
from security.observers.block_observer import BlockObserver
from security.observers.usage_observer import UsageObserver

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_usage_observer_resets_and_prunes_inactive_data(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Reset older days while pruning only ten-day inactivity."""
	now = datetime(2026, 10, 8, 12, tzinfo=UTC)
	for module in ('update', 'deletion'):
		monkeypatch.setattr(
			f'security.monitoring.usage.{module}.'
			'get_utc_datetime_now',
			lambda: now,
		)
	collection = security_collections[MongoDBCollection.USAGE]
	for name, days, day in (
		('old-day', 1, '2026-10-07'),
		('today', 1, '2026-10-08'),
		('boundary', 10, '2026-10-07'),
		('inactive', 11, '2026-10-07'),
	):
		await create_usage_statistics(UsageEntity.USER, name)
		await collection.update_one(
			{'entity_id': name},
			{
				'$set': {
					'usage_day': day,
					'daily_requests': 5,
					'daily_input_tokens': 50,
					'active_ws_connections': ['socket'],
					'last_request_at': now
					- timedelta(days=days),
				}
			},
		)
	await UsageObserver().run_once()
	assert await collection.count_documents({}) == 3
	assert (
		await retrieve_usage_statistics(
			UsageEntity.USER, 'inactive'
		)
		is None
	)
	for name, requests in (('old-day', 0), ('today', 5)):
		stored = await retrieve_usage_statistics(
			UsageEntity.USER, name
		)
		assert stored is not None
		assert stored.usage_day == '2026-10-08'
		assert stored.daily_requests == requests
		assert stored.daily_input_tokens == requests * 10
		assert stored.active_ws_connections == ['socket']
		assert stored.last_request_at == now - timedelta(days=1)


async def test_block_observer_removes_expired_duplicates(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Deny expired blocks until all matches are pruned."""
	now = datetime(2026, 10, 8, 12, tzinfo=UTC)
	monkeypatch.setattr(
		'security.monitoring.blocked.deletion.'
		'get_utc_datetime_now',
		lambda: now,
	)
	expired = BlockedRecord(
		entity=BlockedEntity.USER,
		entity_id='expired',
		blocked_at=now - timedelta(days=1),
		blocked_until=now,
		reason='expired',
	)
	future = expired.model_copy(
		update={
			'entity_id': 'future',
			'blocked_until': now + timedelta(hours=1),
		}
	)
	collection = security_collections[MongoDBCollection.BLOCKED]
	await collection.insert_many(
		[
			expired.model_dump(),
			expired.model_dump(),
			future.model_dump(),
		]
	)
	with pytest.raises(EntityBlockedException):
		await enforce_existing_block(
			BlockedEntity.USER, 'expired'
		)
	await BlockObserver().run_once()
	assert await collection.count_documents({}) == 1
	assert (
		await retrieve_block(BlockedEntity.USER, 'expired')
		is None
	)
	await enforce_existing_block(BlockedEntity.USER, 'expired')
	with pytest.raises(EntityBlockedException):
		await enforce_existing_block(
			BlockedEntity.USER, 'future'
		)
