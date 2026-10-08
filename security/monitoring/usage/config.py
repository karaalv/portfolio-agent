"""Set daily and connection allowances by entity type."""

from schemas.security.monitoring.usage import (
	UsageEntity,
	UsagePolicy,
	UsageScope,
)

USAGE_RETENTION_DAYS = 10

USAGE_POLICY_MAPPING: dict[
	UsageEntity, dict[UsageScope, UsagePolicy]
] = {
	UsageEntity.USER: {
		UsageScope.DAILY_REQUESTS: UsagePolicy(
			UsageScope.DAILY_REQUESTS, 1000
		),
		UsageScope.DAILY_TOKENS: UsagePolicy(
			UsageScope.DAILY_TOKENS, 500_000
		),
		UsageScope.ACTIVE_WS: UsagePolicy(
			UsageScope.ACTIVE_WS, 4
		),
	},
	UsageEntity.IP: {
		UsageScope.DAILY_REQUESTS: UsagePolicy(
			UsageScope.DAILY_REQUESTS, 50_000
		),
		UsageScope.DAILY_TOKENS: UsagePolicy(
			UsageScope.DAILY_TOKENS, 25_000_000
		),
		UsageScope.ACTIVE_WS: UsagePolicy(
			UsageScope.ACTIVE_WS, 200
		),
	},
}


def get_usage_policy(
	entity: UsageEntity, scope: UsageScope
) -> UsagePolicy:
	"""Return the allowance for an entity and usage measure."""
	return USAGE_POLICY_MAPPING[entity][scope]
