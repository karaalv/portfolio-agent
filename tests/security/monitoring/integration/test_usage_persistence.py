"""Exercise usage CRUD, connection tracking and daily resets."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.monitoring.usage import UsageEntity
from security.monitoring.blocked.enforcement import (
	enforce_existing_block,
)
from security.monitoring.blocked.retrieval import retrieve_block
from security.monitoring.usage.creation import (
	create_usage_statistics,
)
from security.monitoring.usage.deletion import (
	delete_usage_statistics,
)
from security.monitoring.usage.retrieval import (
	retrieve_usage_statistics,
)
from security.monitoring.usage.update import (
	add_active_ws_connection,
	clear_active_ws_connections,
	record_request_usage,
	remove_active_ws_connection,
	reset_daily_usage,
)

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_monitoring_maps_to_analytics() -> None:
	"""Production collection resolution uses analytics names."""
	for kind in (
		MongoDBCollection.USAGE,
		MongoDBCollection.BLOCKED,
	):
		collection = get_collection(kind)
		assert collection.database.name == 'analytics'
		assert collection.name == kind.value


@pytest.mark.parametrize('entity', list(UsageEntity))
async def test_usage_create_retrieve_update_delete(
	entity: UsageEntity,
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> None:
	"""Persist both entity kinds with BSON activity dates."""
	created = await create_usage_statistics(entity, 'visitor')
	stored = await retrieve_usage_statistics(entity, 'visitor')
	assert stored is not None
	assert stored.entity == entity
	assert stored.last_request_at.tzinfo == UTC
	assert abs(
		stored.last_request_at - created.last_request_at
	) < (timedelta(milliseconds=1))
	result = await record_request_usage(entity, 'visitor', 42)
	assert result.daily_requests == 1
	assert result.daily_input_tokens == 42
	document = await security_collections[
		MongoDBCollection.USAGE
	].find_one({'entity': entity.value, 'entity_id': 'visitor'})
	assert document is not None
	assert isinstance(document['last_request_at'], datetime)
	assert document['daily_input_tokens'] == 42
	assert await delete_usage_statistics(entity, 'visitor') == 1
	assert await delete_usage_statistics(entity, 'visitor') == 0
	assert (
		await retrieve_usage_statistics(entity, 'visitor')
		is None
	)


async def test_concurrent_creation_and_updates_preserve_usage(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> None:
	"""Retain one record and all concurrent increments."""
	await asyncio.gather(
		*(
			create_usage_statistics(UsageEntity.USER, 'visitor')
			for _ in range(20)
		)
	)
	collection = security_collections[MongoDBCollection.USAGE]
	assert await collection.count_documents({}) == 1
	await asyncio.gather(
		*(
			record_request_usage(UsageEntity.USER, 'visitor', 3)
			for _ in range(20)
		)
	)
	stored = await retrieve_usage_statistics(
		UsageEntity.USER, 'visitor'
	)
	assert stored is not None
	assert stored.daily_requests == 20
	assert stored.daily_input_tokens == 60
	assert (
		await create_usage_statistics(
			UsageEntity.USER, 'visitor'
		)
		== stored
	)


async def test_new_day_resets_once_and_preserves_connections(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Retain new usage during concurrent daily resets."""
	now = datetime(2026, 10, 8, 12, tzinfo=UTC)
	monkeypatch.setattr(
		'security.monitoring.usage.update.get_utc_datetime_now',
		lambda: now,
	)
	await create_usage_statistics(UsageEntity.USER, 'visitor')
	await security_collections[
		MongoDBCollection.USAGE
	].update_one(
		{'entity_id': 'visitor'},
		{
			'$set': {
				'usage_day': '2026-10-07',
				'daily_requests': 900,
				'daily_input_tokens': 400_000,
				'active_ws_connections': ['socket'],
			}
		},
	)
	await asyncio.gather(
		reset_daily_usage(),
		*(
			record_request_usage(UsageEntity.USER, 'visitor', 2)
			for _ in range(20)
		),
	)
	stored = await retrieve_usage_statistics(
		UsageEntity.USER, 'visitor'
	)
	assert stored is not None
	assert stored.usage_day == '2026-10-08'
	assert stored.daily_requests == 20
	assert stored.daily_input_tokens == 40
	assert stored.active_ws_connections == ['socket']
	assert stored.last_request_at == now
	assert await reset_daily_usage() == 0


async def test_fifth_connection_blocks() -> None:
	"""Ignore duplicate IDs and block on connection five."""
	await create_usage_statistics(UsageEntity.USER, 'visitor')
	for index in range(4):
		await add_active_ws_connection(
			UsageEntity.USER, 'visitor', f'socket-{index}'
		)
	duplicate = await add_active_ws_connection(
		UsageEntity.USER, 'visitor', 'socket-0'
	)
	assert len(duplicate.active_ws_connections) == 4
	with pytest.raises(EntityBlockedException):
		await add_active_ws_connection(
			UsageEntity.USER, 'visitor', 'socket-4'
		)
	block = await retrieve_block(BlockedEntity.USER, 'visitor')
	assert block is not None
	assert 'active_ws' in block.reason
	assert await remove_active_ws_connection(
		UsageEntity.USER, 'visitor', 'socket-4'
	)
	assert not await remove_active_ws_connection(
		UsageEntity.USER, 'visitor', 'socket-4'
	)
	with pytest.raises(EntityBlockedException):
		await enforce_existing_block(
			BlockedEntity.USER, 'visitor'
		)


async def test_connection_reset_preserves_counters() -> None:
	"""Startup cleanup clears IDs without resetting usage."""
	for entity in UsageEntity:
		await create_usage_statistics(entity, 'visitor')
		await record_request_usage(entity, 'visitor', 10)
		await add_active_ws_connection(
			entity, 'visitor', 'socket'
		)
	assert await clear_active_ws_connections() == 2
	for entity in UsageEntity:
		stored = await retrieve_usage_statistics(
			entity, 'visitor'
		)
		assert stored is not None
		assert stored.active_ws_connections == []
		assert stored.daily_requests == 1
		assert stored.daily_input_tokens == 10
