"""Core exceptions for the Portfolio Agent application."""

class PortfolioAgentException(Exception):
    """
    Base exception class for the Portfolio 
    Agent application.
    """ 
    def __init__(
        self,
        message: str,
        scope: str,
        module: str,
        operation: str,
    ):
        super().__init__(message)
        self.message = message
        self.scope = scope
        self.module = module
        self.operation = operation

    def __str__(self) -> str:
        """
        Return a string representation of the exception.
        """
        return (
            f'[{self.scope}::{self.module}::{self.operation}] '
            f'{self.message}'
        )