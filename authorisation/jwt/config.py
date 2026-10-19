"""Configure signing and expiry for visitor access tokens."""

from os import getenv

JWT_ALGORITHM = 'HS256'
JWT_TTL_SECONDS = 6 * 24 * 60 * 60  # 6 days in seconds


def get_jwt_secret() -> str:
	"""Read the signing secret after environment loading."""
	secret = getenv('JWT_SECRET')
	if not secret or not secret.strip():
		raise RuntimeError('JWT_SECRET must not be empty.')
	return secret
