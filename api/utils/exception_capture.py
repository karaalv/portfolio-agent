"""Report HTTP failures with server-resolved request context."""

from fastapi import Request
from starlette.exceptions import HTTPException

from api.utils.requests import get_posthog_session_id, get_request_id
from exceptions.core import PortfolioAgentException
from posthog_client.error_tracking import report_exception


def capture_http_failure(request: Request, exc: Exception) -> None:
	"""Classify and report an HTTP handler failure once."""
	status = (
		exc.status_code if isinstance(exc, HTTPException) else 500
	)
	category = (
		'HTTPException'
		if isinstance(exc, HTTPException)
		else 'PortfolioAgentException'
		if isinstance(exc, PortfolioAgentException)
		else 'Exception'
	)
	report_exception(
		exc,
		'http_request_failed',
		{
			'type': category,
			'status_code': status,
			'request_id': get_request_id(request),
			'transport': 'http',
			'http_method': request.method,
			'route': getattr(
				request.scope.get('route'), 'path', None
			),
		},
		user_id=getattr(request.state, 'user_id', None),
		posthog_session_id=get_posthog_session_id(request),
		severity='warning' if 400 <= status < 500 else 'error',
	)
