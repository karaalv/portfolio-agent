"""
Describe WebSocket lifecycle failures with connection context.
"""

from fastapi import WebSocketException

from exceptions.core import PortfolioAgentException


class WebSocketConnectionException(WebSocketException):
	"""Carry context to the registered WebSocket handler."""

	def __init__(
		self,
		connection_id: str,
		request_id: str,
		code: int,
		reason: str,
		user_id: str | None = None,
		posthog_session_id: str | None = None,
	) -> None:
		super().__init__(code=code, reason=reason)
		self.connection_id = connection_id
		self.request_id = request_id
		self.user_id = user_id
		self.posthog_session_id = posthog_session_id


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
