"""Check usage thresholds and database update boundaries."""

from datetime import UTC, datetime
from itertools import product
from unittest.mock import AsyncMock, patch

import pytest
from pymongo import ReturnDocument

from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from schemas.security.monitoring.usage import (
	UsageEntity,
	UsageScope,
	UsageStatistics,
)
from security.monitoring.usage.config import get_usage_policy
from security.monitoring.usage.enforcement import (
	enforce_usage_limits,
)
from security.monitoring.usage.update import (
	record_request_usage,
	reset_daily_usage,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	'entity, scope', list(product(UsageEntity, UsageScope))
)
async def test_block_only_after_exceeding_allowance(
	entity: UsageEntity, scope: UsageScope
) -> None:
	"""Allow the exact limit and block the next operation."""
	statistics = UsageStatistics(entity=entity, entity_id='id')
	limit = get_usage_policy(entity, scope).limit
	attribute = {
		UsageScope.DAILY_REQUESTS: 'daily_requests',
		UsageScope.DAILY_TOKENS: 'daily_input_tokens',
		UsageScope.ACTIVE_WS: 'active_ws_connections',
	}[scope]
	value = (
		[str(index) for index in range(limit)]
		if scope == UsageScope.ACTIVE_WS
		else limit
	)
	setattr(statistics, attribute, value)
	now = datetime(2026, 10, 8, tzinfo=UTC)
	record = BlockedRecord(
		entity=BlockedEntity(entity.value),
		entity_id='id',
		blocked_at=now,
		blocked_until=now,
		reason='threshold',
	)
	with patch(
		'security.monitoring.usage.enforcement.apply_24h_block',
		new_callable=AsyncMock,
		side_effect=EntityBlockedException(record),
	) as block:
		await enforce_usage_limits(statistics)
		block.assert_not_awaited()
		if scope == UsageScope.ACTIVE_WS:
			statistics.active_ws_connections.append('extra')
		else:
			setattr(statistics, attribute, limit + 1)
		with pytest.raises(EntityBlockedException):
			await enforce_usage_limits(statistics)
		block.assert_awaited_once_with(
			BlockedEntity(entity.value),
			'id',
			f'Usage allowance exceeded: {scope.value}.',
		)


async def test_request_uses_updated_statistics() -> None:
	"""Enforce the returned counters after one atomic update."""
	statistics = UsageStatistics(
		entity=UsageEntity.USER,
		entity_id='id',
		daily_requests=2,
		daily_input_tokens=30,
	)
	collection = AsyncMock()
	collection.find_one_and_update.return_value = (
		statistics.model_dump()
	)
	with (
		patch(
			'security.monitoring.usage.update.get_collection',
			return_value=collection,
		),
		patch(
			'security.monitoring.usage.update.'
			'enforce_usage_limits',
			new_callable=AsyncMock,
		) as enforce,
	):
		result = await record_request_usage(
			UsageEntity.USER, 'id', 10
		)
		assert result == statistics
		enforce.assert_awaited_once_with(statistics)
	collection.find_one_and_update.assert_awaited_once()
	call = collection.find_one_and_update.call_args
	assert call.args[0] == {'entity': 'user', 'entity_id': 'id'}
	assert isinstance(call.args[1], list)
	assert call.kwargs == {
		'return_document': ReturnDocument.AFTER
	}
	collection.update_one.assert_not_awaited()


async def test_updates_require_a_created_usage_record() -> None:
	"""Missing records must not create implicit identities."""
	collection = AsyncMock()
	collection.find_one_and_update.return_value = None
	with patch(
		'security.monitoring.usage.update.get_collection',
		return_value=collection,
	):
		with pytest.raises(LookupError):
			await record_request_usage(
				UsageEntity.USER, 'missing'
			)
	collection.insert_one.assert_not_awaited()


async def test_negative_tokens_do_not_write_usage() -> None:
	"""Reject invalid accounting before contacting MongoDB."""
	with patch(
		'security.monitoring.usage.update.get_collection'
	) as get_collection:
		with pytest.raises(ValueError):
			await record_request_usage(
				UsageEntity.USER, 'id', -1
			)
		get_collection.assert_not_called()


async def test_reconciliation_preserves_current_day() -> None:
	"""Preserve current counters and all connection IDs."""
	collection = AsyncMock()
	collection.update_many.return_value.modified_count = 2
	now = datetime(2026, 10, 8, tzinfo=UTC)
	with (
		patch(
			'security.monitoring.usage.update.get_collection',
			return_value=collection,
		),
		patch(
			'security.monitoring.usage.update.'
			'get_utc_datetime_now',
			return_value=now,
		),
	):
		assert await reset_daily_usage() == 2
	collection.update_many.assert_awaited_once_with(
		{'usage_day': {'$lt': '2026-10-08'}},
		{
			'$set': {
				'usage_day': '2026-10-08',
				'daily_requests': 0,
				'daily_input_tokens': 0,
			}
		},
	)
