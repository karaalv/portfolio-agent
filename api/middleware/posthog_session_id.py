"""Retain browser replay context independently of user identity."""

from fastapi import Request
from starlette.middleware.base import (
	BaseHTTPMiddleware,
	RequestResponseEndpoint,
)
from starlette.responses import Response


class PostHogSessionIdMiddleware(BaseHTTPMiddleware):
	"""Copy the optional PostHog session header to request state."""

	async def dispatch(
		self,
		request: Request,
		call_next: RequestResponseEndpoint,
	) -> Response:
		"""Retain supplied IDs without generating replay sessions."""
		session_id = request.headers.get(
			'X-POSTHOG-SESSION-ID', ''
		).strip()
		request.state.posthog_session_id = session_id or None
		return await call_next(request)
