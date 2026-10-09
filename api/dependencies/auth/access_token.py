"""Validate the visitor cookie after the application IP gate."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from api.config.cookies import ACCESS_TOKEN_COOKIE_NAME
from api.dependencies.auth.ip import IPAccess
from authorisation.jwt.validate import validate_token
from exceptions.authorisation import JwtValidationException


async def require_access_token(
	request: Request, _ip_address: IPAccess
) -> str:
	"""Return a verified user ID or an authentication error."""
	token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
	if not token:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='Access token is missing.',
		)
	try:
		payload = validate_token(token)
	except JwtValidationException as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='Access token is invalid or expired.',
		) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail='Unable to validate access token.',
		) from exc
	return payload['sub']


AccessUserId = Annotated[str, Depends(require_access_token)]
