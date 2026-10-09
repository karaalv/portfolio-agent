"""Report persisted security blocks to the API layer."""

from exceptions.core import PortfolioAgentException
from schemas.security.monitoring.blocked import BlockedRecord


class EntityBlockedException(PortfolioAgentException):
	"""Carry the persisted block that prevents an operation."""

	def __init__(self, record: BlockedRecord) -> None:
		"""Attach block metadata for API handling."""
		self.record = record
		super().__init__(
			message=record.reason,
			scope='security',
			module='monitoring.blocked',
			operation='enforce_block',
		)


class SecurityServiceException(PortfolioAgentException):
	"""Report a security service lifecycle failure."""

	def __init__(self, message: str, operation: str) -> None:
		"""Attach the failing security lifecycle operation."""
		super().__init__(
			message=message,
			scope='security',
			module='lifecycle',
			operation=operation,
		)
