"""Structured exceptions for authorisation failures."""

from exceptions.core import PortfolioAgentException


class JwtValidationException(PortfolioAgentException):
	"""Report a token that cannot authenticate a visitor."""

	def __init__(self, message: str):
		"""Attach the JWT validation scope to the failure."""
		super().__init__(
			message=message,
			scope='authorisation',
			module='jwt',
			operation='validate_token',
		)
