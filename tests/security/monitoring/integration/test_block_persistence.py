"""Exercise persisted allowances, block reuse and duplicates."""

import asyncio
from datetime import timedelta
from itertools import product

import pytest
from pymongo.asynchronous.collection import AsyncCollection

from database.mongodb.collections import MongoDBCollection
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.monitoring.usage import (
	UsageEntity,
	UsageScope,
)
from security.monitoring.blocked.creation import create_block
from security.monitoring.blocked.deletion import delete_blocks
from security.monitoring.blocked.enforcement import (
	apply_24h_block,
	enforce_existing_block,
)
from security.monitoring.blocked.retrieval import retrieve_block
from security.monitoring.blocked.update import (
	update_block_reason,
)
from security.monitoring.usage.config import get_usage_policy
from security.monitoring.usage.creation import (
	create_usage_statistics,
)
from security.monitoring.usage.retrieval import (
	retrieve_usage_statistics,
)
from security.monitoring.usage.update import record_request_usage

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


@pytest.mark.parametrize(
	'entity, scope',
	list(
		product(
			UsageEntity,
			(UsageScope.DAILY_REQUESTS, UsageScope.DAILY_TOKENS),
		)
	),
)
async def test_daily_allowance_persists_block_after_limit(
	entity: UsageEntity,
	scope: UsageScope,
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> None:
	"""Allow the last slot and block the next counted request."""
	await create_usage_statistics(entity, 'visitor')
	limit = get_usage_policy(entity, scope).limit
	field = (
		'daily_requests'
		if scope == UsageScope.DAILY_REQUESTS
		else 'daily_input_tokens'
	)
	await security_collections[
		MongoDBCollection.USAGE
	].update_one(
		{'entity': entity.value, 'entity_id': 'visitor'},
		{'$set': {field: limit - 1}},
	)
	tokens = 1 if scope == UsageScope.DAILY_TOKENS else 0
	await record_request_usage(entity, 'visitor', tokens)
	with pytest.raises(EntityBlockedException):
		await record_request_usage(entity, 'visitor', tokens)
	stored = await retrieve_usage_statistics(entity, 'visitor')
	assert stored is not None
	assert getattr(stored, field) == limit + 1
	block = await retrieve_block(
		BlockedEntity(entity.value), 'visitor'
	)
	assert block is not None
	assert scope.value in block.reason
	assert block.blocked_until - block.blocked_at == timedelta(
		hours=24
	)


async def test_concurrent_block_creation_preserves_first_block(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> None:
	"""Reuse one persisted block with stable timestamps."""
	await create_block(BlockedEntity.USER, 'visitor', 'original')
	original = await retrieve_block(
		BlockedEntity.USER, 'visitor'
	)
	assert original is not None
	records = await asyncio.gather(
		*(
			create_block(BlockedEntity.USER, 'visitor', 'repeat')
			for _ in range(20)
		)
	)
	assert all(record == original for record in records)
	assert (
		await security_collections[
			MongoDBCollection.BLOCKED
		].count_documents({})
		== 1
	)
	with pytest.raises(EntityBlockedException) as error:
		await apply_24h_block(
			BlockedEntity.USER, 'visitor', 'new'
		)
	assert error.value.record == original


async def test_explicit_updates_and_duplicate_block_deletion(
	security_collections: dict[
		MongoDBCollection, AsyncCollection
	],
) -> None:
	"""Correct reasons and delete every duplicate block."""
	await create_block(BlockedEntity.IP, 'visitor', 'original')
	original = await retrieve_block(BlockedEntity.IP, 'visitor')
	assert original is not None
	await security_collections[
		MongoDBCollection.BLOCKED
	].insert_one(original.model_dump())
	assert await update_block_reason(
		BlockedEntity.IP, 'visitor', 'corrected'
	)
	stored = await retrieve_block(BlockedEntity.IP, 'visitor')
	assert stored is not None
	assert stored.reason == 'corrected'
	assert stored.blocked_at == original.blocked_at
	assert stored.blocked_until == original.blocked_until
	with pytest.raises(EntityBlockedException):
		await enforce_existing_block(BlockedEntity.IP, 'visitor')
	assert await delete_blocks(BlockedEntity.IP, 'visitor') == 2
	assert (
		await retrieve_block(BlockedEntity.IP, 'visitor') is None
	)
	await enforce_existing_block(BlockedEntity.IP, 'visitor')
	assert await delete_blocks(BlockedEntity.IP, 'visitor') == 0
