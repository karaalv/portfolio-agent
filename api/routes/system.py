"""
System-related API routes for the Portfolio Backend.
"""

from fastapi import APIRouter, Request

from api.utils.requests import get_request_id
from api.utils.responses import create_http_response

# --- Router ---

system_router = APIRouter()

# --- Endpoints ---

@system_router.get("/health")
async def health_check(request: Request):
	"""Report whether the system is running."""
	return create_http_response(
		request_id=get_request_id(request),
		success=True,
		message="System is running.",
		data={"status": "ok"},
		status_code=200
	)