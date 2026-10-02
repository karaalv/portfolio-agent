"""
Exceptions related to agent operations.
"""

from exceptions.core import PortfolioAgentException

class AgentException(PortfolioAgentException):
    """Base exception for agent-related errors."""
    def __init__(
        self,
        message: str,
        module: str,
        operation: str,
    ):
        super().__init__(
            message=message,
            scope="agent",
            module=module,
            operation=operation,
        )