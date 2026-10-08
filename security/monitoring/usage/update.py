"""Record usage atomically and enforce resulting allowances."""

from typing import Any

from pymongo import ReturnDocument

from database.mongodb.collections import MongoDBCollection
from database.mongodb.main import get_collection
from schemas.security.monitoring.usage import (
	UsageEntity,
	UsageStatistics,
)
from security.monitoring.usage.enforcement import (
	enforce_usage_limits,
)
from shared.time import get_utc_datetime_now


async def record_request_usage(
	entity: UsageEntity,
	entity_id: str,
	input_tokens: int = 0,
) -> UsageStatistics:
	"""Count one request and incoming message tokens."""
	if input_tokens < 0:
		raise ValueError('input_tokens must not be negative.')
	now = get_utc_datetime_now()
	today = now.date().isoformat()
	older_day = {'$lt': ['$usage_day', today]}
	statistics = await _update_usage(
		entity,
		entity_id,
		[
			{
				'$set': {
					'usage_day': {
						'$cond': [older_day, today, '$usage_day']
					},
					'daily_requests': {
						'$add': [
							{
								'$cond': [
									older_day,
									0,
									'$daily_requests',
								]
							},
							1,
						]
					},
					'daily_input_tokens': {
						'$add': [
							{
								'$cond': [
									older_day,
									0,
									'$daily_input_tokens',
								]
							},
							input_tokens,
						]
					},
					'last_request_at': now,
				}
			}
		],
	)
	await enforce_usage_limits(statistics)
	return statistics


async def add_active_ws_connection(
	entity: UsageEntity, entity_id: str, connection_id: str
) -> UsageStatistics:
	"""Register one unique connection and enforce allowances."""
	if not connection_id.strip():
		raise ValueError('connection_id must not be empty.')
	await reset_usage_day(entity, entity_id)
	statistics = await _update_usage(
		entity,
		entity_id,
		{'$addToSet': {'active_ws_connections': connection_id}},
	)
	await enforce_usage_limits(statistics)
	return statistics


async def remove_active_ws_connection(
	entity: UsageEntity, entity_id: str, connection_id: str
) -> bool:
	"""Remove a registration, tolerating absent records."""
	result = await get_collection(
		MongoDBCollection.USAGE
	).update_one(
		{'entity': entity.value, 'entity_id': entity_id},
		{'$pull': {'active_ws_connections': connection_id}},
	)
	return result.modified_count > 0


async def reset_usage_day(
	entity: UsageEntity, entity_id: str
) -> bool:
	"""Reset older counters without overwriting today's usage."""
	today = get_utc_datetime_now().date().isoformat()
	result = await get_collection(
		MongoDBCollection.USAGE
	).update_one(
		{
			'entity': entity.value,
			'entity_id': entity_id,
			'usage_day': {'$lt': today},
		},
		{
			'$set': {
				'usage_day': today,
				'daily_requests': 0,
				'daily_input_tokens': 0,
			}
		},
	)
	return result.modified_count > 0


async def reset_daily_usage() -> int:
	"""Reconcile older records with the current UTC date."""
	today = get_utc_datetime_now().date().isoformat()
	result = await get_collection(
		MongoDBCollection.USAGE
	).update_many(
		{'usage_day': {'$lt': today}},
		{
			'$set': {
				'usage_day': today,
				'daily_requests': 0,
				'daily_input_tokens': 0,
			}
		},
	)
	return result.modified_count


async def clear_active_ws_connections() -> int:
	"""Clear stale IDs before accepting connections."""
	result = await get_collection(
		MongoDBCollection.USAGE
	).update_many({}, {'$set': {'active_ws_connections': []}})
	return result.modified_count


async def _update_usage(
	entity: UsageEntity,
	entity_id: str,
	update: dict[str, Any] | list[dict[str, Any]],
) -> UsageStatistics:
	"""Update an existing record and return its new counters."""
	document = await get_collection(
		MongoDBCollection.USAGE
	).find_one_and_update(
		{'entity': entity.value, 'entity_id': entity_id},
		update,
		return_document=ReturnDocument.AFTER,
	)
	if document is None:
		raise LookupError('Usage record has not been created.')
	return UsageStatistics.model_validate(document)
