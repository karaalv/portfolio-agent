"""
This middleware is responsible for generating and attaching
a unique request ID to each incoming API request. This request
ID is used for tracing and debugging purposes.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from shared.ids import generate_uuid_str


class RequestIdMiddleware(BaseHTTPMiddleware):
	async def dispatch(
		self,
		request: Request,
		call_next,
	):
		# Prefer client-supplied header
		req_id = request.headers.get('X-Request-ID')

		# Generate if missing
		if not req_id:
			req_id = generate_uuid_str()

		# Attach to request state
		request.state.request_id = req_id

		# Continue request lifecycle
		response = await call_next(request)

		# Echo back for traceability
		response.headers['X-Request-ID'] = req_id

		return response
