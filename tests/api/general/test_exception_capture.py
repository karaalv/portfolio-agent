"""Exercise production HTTP handlers with isolated telemetry."""

import logging
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request

from api import server
from api.middleware.posthog_session_id import (
	PostHogSessionIdMiddleware,
)
from api.middleware.request_id import RequestIdMiddleware
from api.utils import exception_capture
from exceptions.core import PortfolioAgentException
from posthog_client import error_tracking
from shared.logging.logger import LOGGER_NAME

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	('kind', 'status', 'level'),
	[
		('portfolio', 500, logging.ERROR),
		('unauthorised', 401, logging.WARNING),
		('http_server', 503, logging.ERROR),
		('unexpected', 500, logging.ERROR),
	],
)
async def test_http_handlers_keep_server_identity_and_session(
	monkeypatch,
	caplog,
	kind,
	status,
	level,
):
	"""Return the intended response even if exception upload fails."""
	capture = Mock()
	monkeypatch.setattr(
		error_tracking, 'capture_exception', capture
	)
	app = FastAPI()
	for (
		exception_type,
		handler,
	) in server.app.exception_handlers.items():
		app.add_exception_handler(exception_type, handler)
	app.add_middleware(PostHogSessionIdMiddleware)
	app.add_middleware(RequestIdMiddleware)
	logger = logging.getLogger(LOGGER_NAME)
	logger.addHandler(caplog.handler)

	@app.get('/failure')
	async def failure(request: Request):
		request.state.user_id = 'server-user'
		if kind == 'portfolio':
			raise PortfolioAgentException(
				'failed', 'api', 'test', 'read'
			)
		if kind == 'unauthorised':
			raise HTTPException(
				status_code=401, detail='Access denied'
			)
		if kind == 'http_server':
			raise HTTPException(
				status_code=503, detail='Unavailable'
			)
		raise RuntimeError('unexpected failure')

	try:
		async with httpx.AsyncClient(
			transport=httpx.ASGITransport(
				app=app, raise_app_exceptions=False
			),
			base_url='https://test',
		) as client:
			response = await client.get(
				'/failure',
				headers={
					'X-Request-ID': 'request-1',
					'X-POSTHOG-SESSION-ID': 'session-1',
					'X-POSTHOG-DISTINCT-ID': 'forged-user',
				},
			)
	finally:
		logger.removeHandler(caplog.handler)
	assert response.status_code == status
	capture.assert_called_once()
	assert capture.call_args.args[1] == 'server-user'
	properties = capture.call_args.args[2]
	assert properties['request_id'] == 'request-1'
	assert properties['$session_id'] == 'session-1'
	assert properties['status_code'] == status
	assert properties['route'] == '/failure'
	assert properties['request_url'] == 'https://test/failure'
	assert properties['request_path'] == '/failure'
	assert caplog.records[0].levelno == level


@pytest.mark.parametrize(
	'path',
	[
		'/.env',
		'/.env.production',
		'/config/.env',
		'/config.dev.env',
		'/.git/HEAD',
		'/.GIT/config',
		'/wp-admin/install.php',
		'/wp-login.php',
		'/config.json',
		'/AGENTS.md',
	],
)
def test_scanner_404_skips_failure_telemetry(
	monkeypatch, path: str
) -> None:
	"""Drop known unmatched probes from logs and error capture."""
	report = Mock()
	monkeypatch.setattr(
		exception_capture, 'report_exception', report
	)
	request = _failure_request(path)
	exception_capture.capture_http_failure(
		request, HTTPException(status_code=404)
	)
	report.assert_not_called()


@pytest.mark.parametrize(
	('path', 'status', 'matched'),
	[
		('/api/missing', 404, False),
		('/', 404, False),
		('/favicon.ico', 404, False),
		('/.envoy', 404, False),
		('/.env', 401, False),
		('/.env', 500, False),
		('/api/config', 404, True),
	],
)
def test_other_http_failures_keep_url_context(
	monkeypatch, path: str, status: int, matched: bool
) -> None:
	"""Retain real failures without exposing query credentials."""
	report = Mock()
	monkeypatch.setattr(
		exception_capture, 'report_exception', report
	)
	request = _failure_request(path)
	if matched:
		from fastapi.routing import APIRoute

		request.scope['route'] = APIRoute(
			path, endpoint=lambda: None
		)
	exception_capture.capture_http_failure(
		request, HTTPException(status_code=status)
	)
	report.assert_called_once()
	properties = report.call_args.args[2]
	assert properties['request_url'] == f'https://test{path}'
	assert properties['request_path'] == path
	assert properties['route'] == (path if matched else None)
	assert 'secret-token' not in str(properties)


def _failure_request(path: str) -> Request:
	"""Build request context containing a sensitive query value."""
	return Request(
		{
			'type': 'http',
			'scheme': 'https',
			'server': ('test', 443),
			'path': path,
			'query_string': b'access_token=secret-token&offset=20',
			'headers': [],
			'method': 'GET',
		}
	)


async def test_http_authentication_attaches_verified_identity(
	monkeypatch,
):
	"""Retain the verified token subject for later handler capture."""
	from api.config.cookies import ACCESS_TOKEN_COOKIE_NAME
	from api.dependencies.auth import access_token

	monkeypatch.setattr(
		access_token,
		'validate_token',
		lambda _: {'sub': 'verified'},
	)
	request = Request(
		{
			'type': 'http',
			'headers': [
				(
					b'cookie',
					f'{ACCESS_TOKEN_COOKIE_NAME}=token'.encode(),
				),
				(b'x-posthog-distinct-id', b'forged'),
			],
		}
	)
	assert (
		await access_token.require_access_token(
			request, '127.0.0.1'
		)
		== 'verified'
	)
	assert request.state.user_id == 'verified'
