"""
This module contains utility functions
for API operations.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt

from api.common.config import COOKIE_EXPIRY_SECONDS
from api.common.responses import error_response

# --- Error Handling ---


def api_exception_handler(message: str):
	"""
	Decorator to handle exceptions in API
	functions.
	Example:

	```python
	@router.get("/example")
	@with_api(context="fetch example data")
	async def example_endpoint():
		pass
	```
	"""

	def decorator(func):
		@wraps(func)
		async def wrapper(*args, **kwargs):
			try:
				return await func(*args, **kwargs)
			except Exception as e:
				return error_response(
					message=f'Error in {message}',
					errors=str(e),
				)

		return wrapper

	return decorator


# --- Security Utilities ---


def create_jwt_token(user_id: str) -> str:
	"""
	Creates a JWT token for the user.

	Args:
		user_id (str): The unique identifier for the user.

	Returns:
		str: The generated JWT token.
	"""
	payload = {
		'user_id': user_id,
		'exp': datetime.now(timezone.utc)
		+ timedelta(seconds=COOKIE_EXPIRY_SECONDS),
	}
	return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm='HS256')
