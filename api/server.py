"""Configure the FastAPI application and its lifecycle."""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.common.authentication import verify_frontend_token
from api.common.maintainer import Maintainer
from api.common.responses import error_response

# Routes
from api.routes import agent_routes, user_routes
from common.utils import TerminalColors
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)

# --- Lifecycle Management ---


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Open the database on startup and close it on shutdown."""
	# Startup
	print(
		f'Starting '
		f'{TerminalColors.blue}'
		f'Portfolio Agent API'
		f'{TerminalColors.reset}'
		f'...'
	)

	# 1. Connect to MongoDB
	if not await connect_mongo():
		exit(1)

	# 2. Start the maintainer
	_ = Maintainer()

	print(
		f'{TerminalColors.green}'
		f'Portfolio Agent API '
		f'{TerminalColors.reset}'
		f'Listening on port: '
		f'{TerminalColors.cyan}'
		f'{os.getenv("PORTFOLIO_AGENT_PORT")}'
		f'{TerminalColors.reset}'
	)

	yield

	# Shutdown
	print(
		f'Shutting down '
		f'{TerminalColors.blue}'
		f'Portfolio Agent API'
		f'{TerminalColors.reset}'
		f'...'
	)

	# 1. Close MongoDB connection
	if not await close_mongo():
		exit(1)

	print(
		f'{TerminalColors.green}'
		f'Portfolio Agent API '
		f'{TerminalColors.reset}'
		f'Shutdown complete.'
	)


# --- FastAPI App Initialization ---

app = FastAPI(
	title='Portfolio Agent API',
	description='API for managing portfolio agents.',
	lifespan=lifespan,
	root_path='/api',
)

# --- Middleware ---
origins = os.getenv('CORS_ORIGIN', '').split(',')

app.add_middleware(
	CORSMiddleware,
	allow_origins=[o.strip() for o in origins if o.strip()],
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
	"""Return a standard response for unhandled exceptions."""
	return error_response(
		message='An unexpected error occurred.',
		status_code=500,
		errors=str(exc),
	)


# Health Check Endpoint


@app.get('/health')
async def health_check():
	"""Report whether the API is running."""
	return JSONResponse(content={'status': 'ok'}, status_code=200)


# --- Routes ---

app.include_router(
	router=user_routes.router,
	prefix='/users',
	dependencies=[Depends(verify_frontend_token)],
)

# HTTP and Websocket dependencies handled
# on a per-route basis
app.include_router(
	router=agent_routes.router,
	prefix='/agent',
)
