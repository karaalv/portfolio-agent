"""Configure the visitor's access-token cookie."""

from os import getenv
from typing import Literal

ACCESS_TOKEN_COOKIE_NAME = 'JWT'
ACCESS_TOKEN_COOKIE_PATH = '/'
ACCESS_TOKEN_COOKIE_SECURE = True
ACCESS_TOKEN_COOKIE_HTTPONLY = True
ACCESS_TOKEN_COOKIE_SAMESITE: Literal[
	'lax', 'strict', 'none'
] = 'lax'


def get_cookie_domain() -> str:
	"""Read the required domain after environment loading."""
	domain = getenv('COOKIE_DOMAIN')
	if not domain or not domain.strip():
		raise RuntimeError('COOKIE_DOMAIN must not be empty.')
	return domain.strip()
