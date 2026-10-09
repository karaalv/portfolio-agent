"""Enforce allowed origins for selected application routers."""

from collections.abc import Sequence

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from api.utils.requests import get_request_id
from api.utils.responses import create_http_response


class OriginMiddleware:
	"""Reject HTTP requests and socket handshakes by origin."""

	def __init__(
		self,
		app: ASGIApp,
		allowed_origins: Sequence[str],
		protected_prefixes: Sequence[str],
	) -> None:
		"""Capture allowed origins and router prefixes."""
		self.app = app
		self.allowed_origins = frozenset(allowed_origins)
		self.protected_prefixes = tuple(protected_prefixes)

	async def __call__(
		self,
		scope: Scope,
		receive: Receive,
		send: Send,
	) -> None:
		"""Check protected traffic before routing."""
		if scope['type'] not in {'http', 'websocket'}:
			await self.app(scope, receive, send)
			return
		path = _get_application_path(scope)
		protected = any(
			path == prefix or path.startswith(prefix + '/')
			for prefix in self.protected_prefixes
		)
		if (
			not protected
			or Headers(scope=scope).get('origin')
			in self.allowed_origins
		):
			await self.app(scope, receive, send)
			return
		if scope['type'] == 'websocket':
			await send(
				{
					'type': 'websocket.close',
					'code': 1008,
					'reason': 'Origin is not allowed.',
				}
			)
			return
		response = create_http_response(
			request_id=get_request_id(Request(scope)),
			success=False,
			message='Origin is not allowed.',
			status_code=403,
		)
		await response(scope, receive, send)


def _get_application_path(scope: Scope) -> str:
	"""Resolve paths with or without a deployment root prefix."""
	path = scope['path']
	root_path = scope.get('root_path', '').rstrip('/')
	if root_path and (
		path == root_path or path.startswith(root_path + '/')
	):
		return path[len(root_path) :] or '/'
	return path
