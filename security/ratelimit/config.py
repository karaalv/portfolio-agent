"""Configure rate allowances for expected API usage."""

from schemas.security.ratelimit import (
	RateLimitConfig,
	ResourceAccessor,
	ResourceScope,
)

RESOURCE_LIMITER_CONFIG_MAPPING: dict[
	ResourceScope, dict[ResourceAccessor, RateLimitConfig]
] = {
	ResourceScope.SYSTEM: {
		ResourceAccessor.IP: RateLimitConfig(500, 60),
		ResourceAccessor.USER: RateLimitConfig(100, 60),
	},
	ResourceScope.AGENT_MESSAGE: {
		ResourceAccessor.IP: RateLimitConfig(1000, 60),
		ResourceAccessor.USER: RateLimitConfig(20, 60),
	},
	ResourceScope.APPLICATION: {
		ResourceAccessor.IP: RateLimitConfig(3000, 60),
		ResourceAccessor.USER: RateLimitConfig(60, 60),
	},
}


def get_rate_limit_config(
	resource_scope: ResourceScope,
	resource_accessor: ResourceAccessor,
) -> RateLimitConfig:
	"""Return the configured allowance for a scope and caller."""
	return RESOURCE_LIMITER_CONFIG_MAPPING[resource_scope][
		resource_accessor
	]
