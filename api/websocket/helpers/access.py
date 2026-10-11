"""Resolve anonymous socket identities and access tokens."""

from fastapi import HTTPException, WebSocketException

from api.dependencies.auth.application import (
	require_application_access,
)
from api.websocket import send_connection
from api.websocket.helpers.responses import (
	create_ws_set_user_token_response,
)
from api.websocket.manager import WebSocketManager
from authorisation.jwt.create import create_token
from authorisation.jwt.validate import validate_token
from exceptions.authorisation import JwtValidationException
from schemas.security.monitoring.usage import UsageEntity
from security.monitoring.usage.creation import (
	create_usage_statistics,
)
from users.creation import create_user


async def resolve_ws_user(
	access_token: str | None,
) -> tuple[str, str | None]:
	"""Return an identity and a claim token for new visitors.

	Validate supplied tokens and enforce application access.
	New identities receive their user and usage records here.
	"""
	if access_token is None:
		user = await create_user()
		await create_usage_statistics(
			UsageEntity.USER, user.user_id
		)
		return user.user_id, create_token(user.user_id)
	try:
		payload = validate_token(access_token)
	except JwtValidationException as exc:
		raise WebSocketException(
			code=1008,
			reason='Access token is invalid or expired.',
		) from exc
	except Exception as exc:
		raise WebSocketException(
			code=1011,
			reason='Unable to validate access token.',
		) from exc
	try:
		user_id = await require_application_access(
			payload['sub']
		)
	except HTTPException as exc:
		code = 1008
		if exc.status_code == 429:
			code = 1013
		elif exc.status_code >= 500:
			code = 1011
		raise WebSocketException(
			code=code, reason=str(exc.detail)
		) from exc
	return user_id, None


async def send_claim_token(
	manager: WebSocketManager,
	claim_token: str | None,
) -> None:
	"""Queue a claim token when the connection has a new user."""
	if claim_token is None:
		return
	queued = await send_connection(
		manager.user_id,
		manager.connection_id,
		create_ws_set_user_token_response(claim_token),
	)
	if not queued:
		raise WebSocketException(
			code=1013,
			reason='Unable to queue access token.',
		)
