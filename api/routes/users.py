"""Expose cookie claiming for existing anonymous visitors."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api.config.cookies import (
	ACCESS_TOKEN_COOKIE_HTTPONLY,
	ACCESS_TOKEN_COOKIE_NAME,
	ACCESS_TOKEN_COOKIE_PATH,
	ACCESS_TOKEN_COOKIE_SAMESITE,
	ACCESS_TOKEN_COOKIE_SECURE,
	get_cookie_domain,
)
from api.dependencies.auth._checks import check_entity_block
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response
from authorisation.jwt.validate import validate_token
from exceptions.authorisation import JwtValidationException
from schemas.api.http.users import ClaimCookieRequest
from schemas.security.monitoring.blocked import BlockedEntity
from shared.time import get_utc_datetime_now
from users.retrieval import does_user_exist

# --- Constants ---

router = APIRouter()

# --- User Routes ---


@router.post('/claim-cookie')
async def claim_cookie(
	request: Request,
	body: ClaimCookieRequest,
) -> JSONResponse:
	"""Set a token cookie for an existing, unblocked visitor."""
	try:
		payload = validate_token(body.claim_token)
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
	user_id = payload['sub']
	try:
		user_exists = await does_user_exist(user_id)
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail='Unable to check user existence.',
		) from exc
	if not user_exists:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail='User does not exist.',
		)
	await check_entity_block(BlockedEntity.USER, user_id)
	expires_at = datetime.fromtimestamp(
		payload['exp'], tz=timezone.utc
	)
	remaining_seconds = int(
		(expires_at - get_utc_datetime_now()).total_seconds()
	)
	if remaining_seconds <= 0:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='Access token is invalid or expired.',
		)
	response = create_http_response(
		request_id=get_request_id(request),
		success=True,
		message='Access cookie claimed successfully.',
		data=None,
	)
	response.set_cookie(
		key=ACCESS_TOKEN_COOKIE_NAME,
		value=body.claim_token,
		max_age=remaining_seconds,
		expires=expires_at,
		path=ACCESS_TOKEN_COOKIE_PATH,
		domain=get_cookie_domain(),
		httponly=ACCESS_TOKEN_COOKIE_HTTPONLY,
		secure=ACCESS_TOKEN_COOKIE_SECURE,
		samesite=ACCESS_TOKEN_COOKIE_SAMESITE,
	)
	return response
