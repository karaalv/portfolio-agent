"""Verify optional HTTP replay context without identity changes."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.middleware.posthog_session_id import (
	PostHogSessionIdMiddleware,
)
from api.middleware.request_id import RequestIdMiddleware
from api.utils.requests import get_posthog_session_id, get_request_id

pytestmark = pytest.mark.unit


@pytest.fixture
def app() -> FastAPI:
	"""Expose state through success and handled error paths."""
	application = FastAPI()
	application.add_middleware(PostHogSessionIdMiddleware)
	application.add_middleware(RequestIdMiddleware)

	@application.get('/context')
	async def context(request: Request):
		await asyncio.sleep(0)
		return {
			'session_id': get_posthog_session_id(request),
			'user_id': getattr(request.state, 'user_id', None),
		}

	@application.get('/failure')
	async def failure():
		raise HTTPException(status_code=400, detail='invalid')

	@application.exception_handler(HTTPException)
	async def handle_failure(request: Request, exc: HTTPException):
		return JSONResponse(
			{
				'session_id': get_posthog_session_id(request),
				'request_id': get_request_id(request),
			},
			status_code=exc.status_code,
		)

	return application


@pytest.mark.parametrize(
	('session_id', 'expected'),
	[
		(None, None),
		('', None),
		('   ', None),
		(' session-1 ', 'session-1'),
	],
)
async def test_http_session_context_is_optional(
	app: FastAPI, session_id: str | None, expected: str | None
) -> None:
	"""Trim supplied IDs and never adopt browser user identity."""
	headers = {'X-POSTHOG-DISTINCT-ID': 'forged-user'}
	if session_id is not None:
		headers['x-posthog-session-id'] = session_id
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://test',
	) as client:
		response = await client.get('/context', headers=headers)
	assert response.json() == {
		'session_id': expected,
		'user_id': None,
	}


async def test_concurrent_http_contexts_remain_isolated(app: FastAPI):
	"""Do not retain another request's browser session."""
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://test',
	) as client:
		responses = await asyncio.gather(
			client.get(
				'/context', headers={'X-POSTHOG-SESSION-ID': 'one'}
			),
			client.get(
				'/context', headers={'X-POSTHOG-SESSION-ID': 'two'}
			),
			client.get('/context'),
		)
	assert [
		response.json()['session_id'] for response in responses
	] == ['one', 'two', None]


async def test_error_handler_can_read_session_and_request_id(
	app: FastAPI,
) -> None:
	"""Keep replay context available when a route fails."""
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://test',
	) as client:
		response = await client.get(
			'/failure',
			headers={
				'X-POSTHOG-SESSION-ID': 'session-1',
				'X-Request-ID': 'request-1',
			},
		)
	assert response.status_code == 400
	assert response.json() == {
		'session_id': 'session-1',
		'request_id': 'request-1',
	}


def test_helper_without_middleware_returns_none() -> None:
	"""Support requests without optional correlation middleware."""
	request = Request({'type': 'http', 'headers': []})
	assert get_posthog_session_id(request) is None
