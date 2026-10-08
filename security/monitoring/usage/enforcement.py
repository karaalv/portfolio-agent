"""Compare persisted usage against entity allowances."""

from schemas.security.monitoring.blocked import BlockedEntity
from schemas.security.monitoring.usage import (
	UsageScope,
	UsageStatistics,
)
from security.monitoring.blocked.enforcement import (
	apply_24h_block,
)
from security.monitoring.usage.config import get_usage_policy


async def enforce_usage_limits(
	statistics: UsageStatistics,
) -> None:
	"""Persist a block and raise for excess usage."""
	values = {
		UsageScope.DAILY_REQUESTS: statistics.daily_requests,
		UsageScope.DAILY_TOKENS: statistics.daily_input_tokens,
		UsageScope.ACTIVE_WS: len(
			statistics.active_ws_connections
		),
	}
	for scope, value in values.items():
		policy = get_usage_policy(statistics.entity, scope)
		if value > policy.limit:
			await apply_24h_block(
				BlockedEntity(statistics.entity.value),
				statistics.entity_id,
				f'Usage allowance exceeded: {scope.value}.',
			)
