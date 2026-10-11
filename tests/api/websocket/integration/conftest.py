"""Mount real connection classes in an in-process ASGI app."""

from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.testclient import TestClient

from api.websocket.helpers.responses import (
	create_ws_agent_end_response,
	create_ws_agent_response,
	create_ws_agent_start_response,
)
from api.websocket.registry import WebSocketRegistry
from schemas.agent.streaming.stream_manager import (
	StreamManagerItem,
	StreamManagerItemType,
)
from schemas.api.ws.request import (
	WebSocketRequest,
	WebSocketRequestType,
)
from tests.api.websocket.integration.websocket_harness import (
	WebSocketHarness,
)


@pytest.fixture
def harness() -> Iterator[WebSocketHarness]:
	"""Use real ASGI sockets with no port or external clients."""
	registry: WebSocketRegistry | None = None

	@asynccontextmanager
	async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
		"""Create and dispose async state on the serving loop."""
		nonlocal registry
		registry = WebSocketRegistry()
		registry.start()
		try:
			yield
		finally:
			await registry.stop()

	app = FastAPI(lifespan=lifespan)

	@app.websocket('/ws/{user_id}/{connection_id}')
	async def echo(
		websocket: WebSocket, user_id: str, connection_id: str
	) -> None:
		"""
		Exercise protocol delivery without a production route.
		"""
		assert registry is not None
		await websocket.accept()
		manager = await registry.add_connection(
			user_id, connection_id, websocket
		)
		try:
			while True:
				request = WebSocketRequest.model_validate_json(
					await websocket.receive_text()
				)
				if (
					request.type
					== WebSocketRequestType.HEARTBEAT
				):
					continue
				manager.record_message('echo-request')
				item = StreamManagerItem(
					type=StreamManagerItemType.TEXT,
					user_id=user_id,
					memory_id='echo-memory',
					sequence_number=1,
					payload=request.payload,
				)
				for response in (
					create_ws_agent_start_response(
						'echo-request', 'Started'
					),
					create_ws_agent_response(
						'echo-request', item
					),
					create_ws_agent_end_response(
						'echo-request', 'Finished'
					),
				):
					await registry.send_connection(
						user_id, connection_id, response
					)
		except WebSocketDisconnect:
			pass
		finally:
			await registry.remove_connection(
				user_id, connection_id
			)

	with TestClient(app) as client:
		assert registry is not None
		yield WebSocketHarness(client, registry)
