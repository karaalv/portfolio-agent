"""Verify scoped Origin enforcement before route execution."""

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware

pytestmark = pytest.mark.unit
ALLOWED_ORIGIN = 'https://portfolio.test'


@pytest.mark.parametrize(
	'path', ['/users', '/users/claim-cookie', '/agent/chat']
)
@pytest.mark.parametrize(
	'origin', [None, 'null', 'https://other.test']
)
async def test_protected_paths_reject_before_handlers(
	path: str,
	origin: str | None,
) -> None:
	"""Deny bad origins before performing route work."""
	app = _create_app()
	headers = {'X-Request-ID': 'origin-test'}
	if origin is not None:
		headers['Origin'] = origin
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://api.test',
	) as client:
		response = await client.get(path, headers=headers)
	assert response.status_code == 403
	assert response.json()['data'] is None
	assert response.json()['meta']['request_id'] == 'origin-test'
	assert response.headers['X-Request-ID'] == 'origin-test'
	assert app.state.requests == 0


@pytest.mark.parametrize(
	'path, origin',
	[
		('/users/me', ALLOWED_ORIGIN),
		('/agent/chat', ALLOWED_ORIGIN),
		('/api/users/me', ALLOWED_ORIGIN),
		('/system/health', None),
		('/api/system/health', 'https://other.test'),
		('/users-archive', None),
		('/agent-tools', None),
	],
)
async def test_allowlist_and_scope_boundaries(
	path: str,
	origin: str | None,
) -> None:
	"""Allow trusted traffic and exempt other paths."""
	app = _create_app()
	headers = {'Origin': origin} if origin is not None else {}
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://api.test',
	) as client:
		response = await client.get(path, headers=headers)
	assert response.status_code == 200
	assert app.state.requests == 1
	if origin == ALLOWED_ORIGIN:
		assert (
			response.headers['access-control-allow-origin']
			== ALLOWED_ORIGIN
		)


@pytest.mark.parametrize(
	'origin, expected',
	[(ALLOWED_ORIGIN, 200), ('https://other.test', 400)],
)
async def test_cors_still_handles_preflight(
	origin: str,
	expected: int,
) -> None:
	"""Preserve preflight responses without route work."""
	app = _create_app()
	async with httpx.AsyncClient(
		transport=httpx.ASGITransport(app=app),
		base_url='https://api.test',
	) as client:
		response = await client.options(
			'/users/claim-cookie',
			headers={
				'Origin': origin,
				'Access-Control-Request-Method': 'POST',
			},
		)
	assert response.status_code == expected
	assert app.state.requests == 0


@pytest.mark.parametrize(
	'origin', [None, 'null', 'https://other.test']
)
async def test_socket_handshake_rejected_before_app(
	origin: str | None,
) -> None:
	"""Prevent untrusted sockets from reaching the controller."""
	app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
	middleware = OriginMiddleware(
		app, [ALLOWED_ORIGIN], ['/users', '/agent']
	)
	headers = (
		[(b'origin', origin.encode())]
		if origin is not None
		else []
	)
	await middleware(
		{
			'type': 'websocket',
			'path': '/api/agent/chat',
			'root_path': '/api',
			'headers': headers,
		},
		receive,
		send,
	)
	app.assert_not_awaited()
	send.assert_awaited_once_with(
		{
			'type': 'websocket.close',
			'code': 1008,
			'reason': 'Origin is not allowed.',
		}
	)


async def test_allowed_sockets_and_lifespan_pass_through() -> (
	None
):
	"""Pass trusted sockets and non-request scopes unchanged."""
	app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
	middleware = OriginMiddleware(
		app, [ALLOWED_ORIGIN], ['/users', '/agent']
	)
	for scope in [
		{
			'type': 'websocket',
			'path': '/agent/chat',
			'headers': [(b'origin', ALLOWED_ORIGIN.encode())],
		},
		{
			'type': 'websocket',
			'path': '/system/socket',
			'headers': [],
		},
		{'type': 'lifespan'},
	]:
		await middleware(scope, receive, send)
		app.assert_awaited_with(scope, receive, send)
	assert app.await_count == 3
	send.assert_not_awaited()


def _create_app() -> FastAPI:
	"""Match middleware ordering without service startup."""
	app = FastAPI(root_path='/api')
	app.state.requests = 0

	@app.get('/{path:path}')
	async def handle_request(path: str) -> dict[str, str]:
		app.state.requests += 1
		return {'path': path}

	app.add_middleware(
		OriginMiddleware,
		allowed_origins=[ALLOWED_ORIGIN],
		protected_prefixes=('/users', '/agent'),
	)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=[ALLOWED_ORIGIN],
		allow_methods=['*'],
		allow_headers=['*'],
		allow_credentials=True,
	)
	app.add_middleware(RequestIdMiddleware)
	return app
