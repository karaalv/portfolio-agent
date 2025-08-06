"""
Main entry point for the API,
other routes are imported.
"""
import os
from dotenv import load_dotenv 

# Load environment
if os.getenv("ENVIRONMENT") == "test":
    # Load test environment variables
    load_dotenv(
        override=True, 
        dotenv_path=os.path.abspath(".env.test")
    )
else:
    # Load default environment variables
    load_dotenv(
        override=True, 
        dotenv_path=os.path.abspath(".env")
    )

from common.utils import TerminalColors
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from database.mongodb.config import connect_mongo, close_mongo
from api.common.responses import error_response
from api.common.authentication import verify_frontend_token, verify_jwt

from api.routes import user_routes

# --- Lifecycle Management ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle management for the FastAPI app,
    manages startup and shutdown events.
    """
    # Startup 
    print(
        f"Starting "
        f"{TerminalColors.blue}"
        f"Portfolio Agent API"
        f"{TerminalColors.reset}"
        f"..."
    )

    # 1. Connect to MongoDB
    if not await connect_mongo():
        exit(1)

    print(
        f"{TerminalColors.green}"
        f"Portfolio Agent API "
        f"{TerminalColors.reset}"
        f"Listening on port: "
        f"{TerminalColors.cyan}"
        f"{os.getenv('PORT')}"
        f"{TerminalColors.reset}"
    )

    yield

    # Shutdown
    print(
        f"Shutting down "
        f"{TerminalColors.blue}"
        f"Portfolio Agent API"
        f"{TerminalColors.reset}"
        f"..."
    )

    # 1. Close MongoDB connection
    if not await close_mongo():
        exit(1)

    print(
        f"{TerminalColors.green}"
        f"Portfolio Agent API "
        f"{TerminalColors.reset}"
        f"Shutdown complete."
    )

# --- FastAPI App Initialization ---

app = FastAPI(
    title="Portfolio Agent API",
    description="API for managing portfolio agents.",
    lifespan=lifespan,
    root_path="/api",
)

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=str(os.getenv("CORS_ORIGIN")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for the API.
    Returns a standardized error response.
    """
    return error_response(
        message="An unexpected error occurred.",
        status_code=500,
        errors=str(exc)
    )

# Health Check Endpoint

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify 
    the API is running.

    Returns:
        dict: A simple health check response.
    """
    return JSONResponse(
        content={"status": "ok"},
        status_code=200
    )

# --- Routes ---

app.include_router(
    user_routes.router,
    prefix="/users",
    dependencies=[
        Depends(verify_frontend_token)
    ]
)
    
# --- Run Server ---

if __name__ == "__main__":
    import uvicorn
    
    env = os.getenv("ENVIRONMENT")

    if env == "development":
        uvicorn.run(
            app="api.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 3001)),
            log_level="debug",
            reload=True,
        )
    elif env == "production":
        uvicorn.run(
            app="api.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 3001)),
            log_level="debug",
            reload=False,
        )
    elif env == "test":
        uvicorn.run(
            app="api.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 9001)),
            reload=False,
        )
    elif env == "staging":
        uvicorn.run(
            app="api.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 3001)),
            log_level="debug",
            reload=False,
        )
    else:
        print(
            f"{TerminalColors.red}"
            f"Invalid environment: {env}"
            f"{TerminalColors.reset}"
        )
        exit(1)