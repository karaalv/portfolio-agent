"""Access in-process WebSocket state on its owning event loop."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial

from starlette.testclient import TestClient

from api.websocket.registry import WebSocketRegistry


@dataclass
class WebSocketHarness:
	"""Run registry operations on the app's own event loop."""

	client: TestClient
	registry: WebSocketRegistry

	def call[T, **P](
		self,
		function: Callable[P, Awaitable[T]],
		*args: P.args,
		**kwargs: P.kwargs,
	) -> T:
		"""
		Cross the TestClient thread boundary through its portal.
		"""
		assert self.client.portal is not None
		return self.client.portal.call(
			partial(function, *args, **kwargs)
		)
