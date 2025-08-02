"""
This module contains utility functions
used across the backend.
"""
from datetime import datetime, timezone
from typing import Callable, Any, TypeVar, Optional
from functools import wraps

# --- Terminal Colors ---

class TerminalColors:
    """
    A class to hold terminal color codes for
    better readability in terminal outputs.
    """
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    reset = "\033[0m"

# --- Decorators ---

# Generic type for the decorator
T = TypeVar('T', bound=Callable[..., Any])

def handle_exceptions(context: str):
    """
    Decorator to wrap function calls
    with exception handling. It prints 
    the error message to the terminal
    and raises a new exception with 
    context.

    Args:
        context (str): A string describing the context
                       in which the function is called.
    
    Example:
        @handle_exceptions("example_context")
        def my_function():
            # Function logic here
            pass
    """
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(
                    f"{TerminalColors.red}"
                    f"Error in {context}:"
                    f"{TerminalColors.reset}"
                    f" {e}"
                )
                raise Exception(
                    f"Error in application with context "
                    f"'{context}': {e}"
                ) from e
        return wrapper # type: ignore
    return decorator

def handle_exceptions_async(context: str):
    """
    Asynchronous version of the handle_exceptions decorator.
    It wraps async functions with exception handling.

    Args:
        context (str): A string describing the context
                       in which the function is called.
    """
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                print(
                    f"{TerminalColors.red}"
                    f"Error in {context}:"
                    f"{TerminalColors.reset}"
                    f" {e}"
                )
                raise Exception(
                    f"Error in application with context "
                    f"'{context}': {e}"
                ) from e
        return wrapper # type: ignore
    return decorator

# --- Time Utilities ---

def get_timestamp() -> str:
    """
    Returns the current timestamp in 
    ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def get_datetime(timestamp: Optional[str] = None) -> datetime:
    """
    Converts a timestamp string (ISO 8601 
    format) to a datetime object if provided
    else returns current datetime.
    """
    if not timestamp:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))