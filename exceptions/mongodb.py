"""
MongoDB-related exceptions for the Portfolio Agent application.
"""

from exceptions.core import PortfolioAgentException


class MongoDBException(PortfolioAgentException):
	"""
	Base exception class for MongoDB-related errors
	in the Portfolio Agent application.
	"""

	def __init__(
		self,
		message: str,
		module: str,
		operation: str,
	):
		super().__init__(
			message=message,
			scope='mongodb',
			module=module,
			operation=operation,
		)
