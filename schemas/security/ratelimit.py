"""Define scopes, configuration and stored rate limiters."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from aiolimiter import AsyncLimiter

from shared.ids import generate_uuid_str
from shared.time import get_utc_datetime_now


class ResourceAccessor(StrEnum):
	"""Identify the caller whose allowance is being tracked."""

	IP = 'ip'
	USER = 'user'


class ResourceScope(StrEnum):
	"""Separate allowances for different API operations."""

	SYSTEM = 'system'
	AGENT_MESSAGE = 'agent_message'
	APPLICATION = 'application'


@dataclass(slots=True)
class RateLimitConfig:
	"""Set capacity and replenishment period in seconds."""

	max_rate: int
	time_period: int


@dataclass(slots=True)
class RateLimiter:
	"""Track a caller's limiter within a resource scope."""

	resource_scope: ResourceScope
	resource_accessor: ResourceAccessor
	identifier_value: str
	limiter: AsyncLimiter
	last_accessed_at: datetime = field(
		default_factory=get_utc_datetime_now
	)
	limiter_id: str = field(default_factory=generate_uuid_str)
