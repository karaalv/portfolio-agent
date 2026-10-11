"""
Describe WebSocket lifecycle failures with connection context.
"""

from exceptions.core import PortfolioAgentException


class WebSocketManagerException(PortfolioAgentException):
	"""Identify a failed operation on one connection manager."""

	def __init__(
		self,
		message: str,
		operation: str,
		connection_id: str,
		user_id: str,
		request_id: str | None,
	) -> None:
		"""
		Attach identifiers for terminal and future error logging.
		"""
		self.connection_id = connection_id
		self.user_id = user_id
		self.request_id = request_id
		super().__init__(
			message=message,
			scope='api',
			module='websocket.manager',
			operation=operation,
		)


class WebSocketRegistryException(PortfolioAgentException):
	"""
	Report invalid registry lifecycle or registration state.
	"""

	def __init__(self, message: str, operation: str) -> None:
		"""Identify the registry operation that failed."""
		super().__init__(
			message=message,
			scope='api',
			module='websocket.registry',
			operation=operation,
		)
