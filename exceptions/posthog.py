"""PostHog client configuration and lifecycle exceptions."""

from exceptions.core import PortfolioAgentException


class PostHogException(PortfolioAgentException):
	"""Report invalid configuration or an unavailable client."""

	def __init__(
		self,
		message: str,
		module: str,
		operation: str,
	):
		super().__init__(
			message=message,
			scope='posthog',
			module=module,
			operation=operation,
		)
