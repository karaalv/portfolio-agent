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
