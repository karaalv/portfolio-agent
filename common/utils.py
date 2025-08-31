"""
This module contains utility functions
used across the backend.
"""

import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

# --- Terminal Colors ---


class TerminalColors:
	"""
	A class to hold terminal color codes for
	better readability in terminal outputs.
	"""

	red = '\033[31m'
	green = '\033[32m'
	yellow = '\033[33m'
	blue = '\033[34m'
	magenta = '\033[35m'
	cyan = '\033[36m'
	reset = '\033[0m'


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
					f'{TerminalColors.red}'
					f'Error in {context}:'
					f'{TerminalColors.reset}'
					f' {e}'
				)
				raise Exception(
					f"Error in application with context '{context}': {e}"
				) from e

		return wrapper  # type: ignore

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
					f'{TerminalColors.red}'
					f'Error in {context}:'
					f'{TerminalColors.reset}'
					f' {e}'
				)
				raise Exception(
					f"Error in application with context '{context}': {e}"
				) from e

		return wrapper  # type: ignore

	return decorator


# --- Time Utilities ---


def get_timestamp() -> str:
	"""
	Returns the current timestamp in
	ISO 8601 format.
	"""
	return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def get_datetime(
	timestamp: Optional[str] = None,
) -> datetime:
	"""
	Converts a timestamp string (ISO 8601
	format) to a datetime object if provided
	else returns current datetime.
	"""
	if not timestamp:
		return datetime.now(timezone.utc)
	return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class Timer:
	def __init__(self, start: bool = False):
		self.start_time = 0.0
		self.stop_time = 0.0
		self.prev_time = 0.0

		if start:
			self.start_time = time.perf_counter()
			self.stop_time = self.start_time
			self.prev_time = self.start_time

	def start(self):
		self.start_time = time.perf_counter()
		self.prev_time = self.start_time

	def stop(self) -> float:
		self.stop_time = time.perf_counter()
		return self.stop_time - self.start_time

	def elapsed(self) -> float:
		current_time = time.perf_counter()
		delta = current_time - self.prev_time
		self.prev_time = current_time
		return delta
