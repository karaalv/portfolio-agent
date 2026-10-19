"""Validate signed access tokens before trusting identities."""

from typing import Any

import jwt

from authorisation.jwt.config import (
	JWT_ALGORITHM,
	get_jwt_secret,
)
from exceptions.authorisation import JwtValidationException


def validate_token(token: str) -> dict[str, Any]:
	"""Verify signature, expiry and required identity claims."""
	secret = get_jwt_secret()
	if not isinstance(token, str) or not token.strip():
		raise JwtValidationException('Token must not be empty.')
	try:
		payload = jwt.decode(
			token,
			secret,
			algorithms=[JWT_ALGORITHM],
			options={'require': ['sub', 'iat', 'exp']},
		)
	except jwt.ExpiredSignatureError as exc:
		raise JwtValidationException('Token expired.') from exc
	except jwt.InvalidTokenError as exc:
		raise JwtValidationException('Invalid token.') from exc
	if (
		not isinstance(payload['sub'], str)
		or not payload['sub'].strip()
	):
		raise JwtValidationException(
			'Token subject must be a non-empty user ID.'
		)
	return payload
