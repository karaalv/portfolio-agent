"""OpenAI-related exceptions for the Portfolio Agent."""

from exceptions.core import PortfolioAgentException


class OpenAIException(PortfolioAgentException):
	"""
	Base exception for OpenAI-related errors
	in the Portfolio Agent.
	"""

	def __init__(
		self,
		message: str,
		module: str,
		operation: str,
	):
		super().__init__(
			message=message,
			scope='openai',
			module=module,
			operation=operation,
		)
