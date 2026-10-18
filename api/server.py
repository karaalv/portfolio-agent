"""Configure the FastAPI application and its lifecycle."""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from api.dependencies.auth.ip import require_ip_access
from api.lifecycle.config import (
	start_api_lifecycle,
	stop_api_lifecycle,
)
from api.lifecycle.logging import (
	capture_lifecycle_failure,
	log_server_started,
	stop_component,
)
from api.maintenance.maintenance_manager import (
	MaintenanceManager,
)
from api.middleware.origin import OriginMiddleware
from api.middleware.posthog_session_id import (
	PostHogSessionIdMiddleware,
)
from api.middleware.request_id import RequestIdMiddleware
from api.routes.agent import agent_router
from api.routes.agent_memory import agent_memory_router
from api.routes.system import system_router
from api.routes.users import users_router
from api.security.security_manager import SecurityManager
from api.utils.cors import get_allowed_origins
from api.utils.exception_capture import capture_http_failure
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response
from api.websocket.helpers.exception_capture import (
	handle_connection_exception,
)
from exceptions.core import PortfolioAgentException
from exceptions.websocket import WebSocketConnectionException
from shared.logging import LogStyle, rich_print

# --- Lifecycle Management ---


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
	"""Start services and clean up when server shutdown begins.

	Uvicorn handles SIGINT and SIGTERM and ends this lifespan.
	The cleanup path also covers interrupted or failed startup.
	"""
	maintenance_manager = MaintenanceManager()
	security_manager = SecurityManager()
	started = perf_counter()
	component = 'api_clients'
	try:
		try:
			await start_api_lifecycle()
			component = 'security'
			await security_manager.start()
			component = 'maintenance'
			maintenance_manager.start()
			log_server_started(app.version, started)
		except Exception as exc:
			capture_lifecycle_failure(exc, 'startup', component)
			raise
		yield
	finally:
		shutdown_started = perf_counter()
		rich_print(
			'Server termination detected. Shutting down services...',
			style=LogStyle.INFO,
			prefix='api.server',
		)
		try:
			await stop_component(
				maintenance_manager.stop, 'maintenance'
			)
		finally:
			try:
				await stop_component(
					security_manager.stop, 'security'
				)
			finally:
				await stop_api_lifecycle(
					shutdown_failed=sys.exception() is not None,
					shutdown_started=shutdown_started,
				)
		rich_print(
			'Server shutdown complete.',
			style=LogStyle.SUCCESS,
			prefix='api.server',
		)


# --- FastAPI App Initialization ---

app = FastAPI(
	title='Portfolio Backend API',
	description='API for managing portfolio backend.',
	lifespan=lifespan,
	root_path='/api',
	version='2.0.0',
)

# --- Middleware ---

# - Exception Handling -


@app.exception_handler(PortfolioAgentException)
async def portfolio_agent_exception_handler(
	request: Request, exc: PortfolioAgentException
) -> JSONResponse:
	# Handle PortfolioAgentException
	capture_http_failure(request, exc)
	request_id = get_request_id(request)
	return create_http_response(
		request_id=request_id,
		success=False,
		message=exc.message,
		data=None,
		status_code=500,
	)


@app.exception_handler(HTTPException)
async def http_exception_handler(
	request: Request, exc: HTTPException
) -> JSONResponse:
	# Handle HTTPException
	capture_http_failure(request, exc)
	request_id = get_request_id(request)
	exc_message = (
		str(exc.detail) if hasattr(exc, 'detail') else str(exc)
	)
	exc_code = exc.status_code if hasattr(exc, 'status_code') else 500
	return create_http_response(
		request_id=request_id,
		success=False,
		message=exc_message,
		data=None,
		status_code=exc_code,
	)


@app.exception_handler(Exception)
async def general_exception_handler(
	request: Request, exc: Exception
) -> JSONResponse:
	# Handle general exceptions
	capture_http_failure(request, exc)
	request_id = get_request_id(request)
	return create_http_response(
		request_id=request_id,
		success=False,
		message=str(exc),
		data=None,
		status_code=500,
	)


@app.exception_handler(WebSocketConnectionException)
async def websocket_connection_exception_handler(
	websocket: WebSocket, exc: WebSocketConnectionException
) -> None:
	"""Report and close failed handshakes or active connections."""
	await handle_connection_exception(websocket, exc)


# - CORS Configuration -

app.add_middleware(
	OriginMiddleware,
	allowed_origins=get_allowed_origins(),
	protected_prefixes=('/users', '/agent', '/agent-memory'),
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=get_allowed_origins(),
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)

# - Request Correlation Middleware -

app.add_middleware(PostHogSessionIdMiddleware)
app.add_middleware(RequestIdMiddleware)


# Health Check Endpoint

# --- Routes ---

app.include_router(
	router=system_router,
	prefix='/system',
	tags=['System'],
	dependencies=[Depends(require_ip_access)],
)

app.include_router(
	router=users_router,
	prefix='/users',
	tags=['Users'],
	dependencies=[Depends(require_ip_access)],
)

# HTTP and Websocket dependencies handled
# on a per-route basis
app.include_router(
	router=agent_router,
	prefix='/agent',
	tags=['Agent'],
)

app.include_router(
	router=agent_memory_router,
	prefix='/agent-memory',
	tags=['Agent Memory'],
	dependencies=[Depends(require_ip_access)],
)
