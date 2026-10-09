"""Configure the FastAPI application and its lifecycle."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencies.auth.ip import require_ip_access
from api.lifecycle.config import (
	start_api_lifecycle,
	stop_api_lifecycle,
)
from api.maintenance.maintenance_manager import (
	MaintenanceManager,
)
from api.middleware.origin import OriginMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.routes.agent import agent_router
from api.routes.agent_memory import agent_memory_router
from api.routes.system import system_router
from api.routes.users import users_router
from api.security.security_manager import SecurityManager
from api.utils.cors import get_allowed_origins
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response
from exceptions.core import PortfolioAgentException

# --- Lifecycle Management ---


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Start services and stop background work before clients."""
	maintenance_manager = MaintenanceManager()
	security_manager = SecurityManager()
	await start_api_lifecycle()
	try:
		await security_manager.start()
		maintenance_manager.start()
		yield
	finally:
		try:
			await maintenance_manager.stop()
		finally:
			try:
				await security_manager.stop()
			finally:
				await stop_api_lifecycle()


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
async def PORTFOLIO_AGENT_exception_handler(
	request: Request, exc: PortfolioAgentException
) -> JSONResponse:
	# Handle PortfolioAgentException
	request_id = get_request_id(request)
	return create_http_response(
		request_id=request_id,
		success=False,
		message=exc.message,
		data=None,
		status_code=400,
	)


@app.exception_handler(HTTPException)
async def http_exception_handler(
	request: Request, exc: HTTPException
) -> JSONResponse:
	# Handle HTTPException
	request_id = get_request_id(request)
	exc_message = (
		str(exc.detail) if hasattr(exc, 'detail') else str(exc)
	)
	exc_code = (
		exc.status_code if hasattr(exc, 'status_code') else 500
	)
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
	request_id = get_request_id(request)
	return create_http_response(
		request_id=request_id,
		success=False,
		message=str(exc),
		data=None,
		status_code=500,
	)


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

# - Request ID Middleware -

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
