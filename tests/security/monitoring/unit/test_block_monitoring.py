"""Check block persistence, reuse and delayed unblocking."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from security.monitoring.blocked.creation import create_block
from security.monitoring.blocked.enforcement import (
	apply_24h_block,
	enforce_existing_block,
)

pytestmark = pytest.mark.unit


async def test_concurrent_blocks_reuse_original_record() -> None:
	"""Serialize creation without extending an existing block."""
	documents: list[dict] = []

	async def retrieve(*args) -> BlockedRecord | None:
		await asyncio.sleep(0)
		if not documents:
			return None
		return BlockedRecord.model_validate(documents[0])

	collection = AsyncMock()
	collection.insert_one.side_effect = documents.append
	with (
		patch(
			'security.monitoring.blocked.creation.'
			'_creation_lock',
			asyncio.Lock(),
		),
		patch(
			'security.monitoring.blocked.creation.'
			'retrieve_block',
			new_callable=AsyncMock,
			side_effect=retrieve,
		),
		patch(
			'security.monitoring.blocked.creation.'
			'get_collection',
			return_value=collection,
		),
	):
		records = await asyncio.gather(
			*(
				create_block(
					BlockedEntity.USER, 'id', f'reason-{index}'
				)
				for index in range(20)
			)
		)
	collection.insert_one.assert_awaited_once()
	assert all(record == records[0] for record in records)
	assert records[0].reason == 'reason-0'
	assert records[0].blocked_until - records[0].blocked_at == (
		timedelta(hours=24)
	)


async def test_storage_failure_is_not_reported_as_a_block() -> (
	None
):
	"""Do not claim persistence succeeded when MongoDB fails."""
	collection = AsyncMock()
	collection.insert_one.side_effect = RuntimeError('offline')
	with (
		patch(
			'security.monitoring.blocked.creation.'
			'retrieve_block',
			new_callable=AsyncMock,
			return_value=None,
		),
		patch(
			'security.monitoring.blocked.creation.'
			'get_collection',
			return_value=collection,
		),
	):
		with pytest.raises(RuntimeError, match='offline'):
			await apply_24h_block(
				BlockedEntity.USER, 'id', 'limit'
			)


async def test_expired_record_still_denies_access() -> None:
	"""Only deleting a block restores access."""
	now = datetime(2026, 10, 8, tzinfo=UTC)
	record = BlockedRecord(
		entity=BlockedEntity.IP,
		entity_id='127.0.0.1',
		blocked_at=now - timedelta(days=2),
		blocked_until=now - timedelta(days=1),
		reason='limit',
	)
	with patch(
		'security.monitoring.blocked.enforcement.retrieve_block',
		new_callable=AsyncMock,
		return_value=record,
	):
		with pytest.raises(EntityBlockedException) as error:
			await enforce_existing_block(
				BlockedEntity.IP, '127.0.0.1'
			)
		assert error.value.record == record
