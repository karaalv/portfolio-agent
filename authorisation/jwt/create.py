"""Issue signed access tokens for anonymous visitors."""

from datetime import timedelta

import jwt

from authorisation.jwt.config import (
	JWT_ALGORITHM,
	JWT_TTL_SECONDS,
	get_jwt_secret,
)
from shared.time import get_utc_datetime_now


def create_token(user_id: str) -> str:
	"""Sign a visitor identity with a fixed six-day expiry."""
	if not isinstance(user_id, str) or not user_id.strip():
		raise ValueError('user_id must be a non-empty string.')
	now = get_utc_datetime_now()
	return jwt.encode(
		{
			'sub': user_id,
			'iat': now,
			'exp': now + timedelta(seconds=JWT_TTL_SECONDS),
		},
		get_jwt_secret(),
		algorithm=JWT_ALGORITHM,
	)
