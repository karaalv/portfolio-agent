"""Report HTTP failures with server-resolved request context."""

import re

from fastapi import Request
from starlette.exceptions import HTTPException

from api.config.observability import SCANNER_PATH_PATTERNS
from api.utils.requests import (
	get_posthog_session_id,
	get_request_id,
)
from exceptions.core import PortfolioAgentException
from posthog_client.error_tracking import report_exception


def capture_http_failure(
	request: Request, exc: Exception
) -> None:
	"""Classify and report an HTTP handler failure once."""
	status = (
		exc.status_code
		if isinstance(exc, HTTPException)
		else 500
	)
	if status == 404 and _is_scanner_request(request):
		return
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
			'request_url': str(
				request.url.replace(query='', fragment='')
			),
			'request_path': request.url.path,
			'route': getattr(
				request.scope.get('route'), 'path', None
			),
		},
		user_id=getattr(request.state, 'user_id', None),
		posthog_session_id=get_posthog_session_id(request),
		severity='warning' if 400 <= status < 500 else 'error',
	)


def _is_scanner_request(request: Request) -> bool:
	"""Match known probes only when no application route matched.

	Do not suppress failures raised by registered API routes.
	The HTTP response and server access log remain unchanged.
	"""
	if request.scope.get('route') is not None:
		return False
	path = request.url.path.casefold()
	return any(
		re.search(pattern, path) is not None
		for pattern in SCANNER_PATH_PATTERNS
	)
