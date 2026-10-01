"""Configuration for the API lifecycle"""

from os import getenv

from api.lifecycle.environment import load_environment_variables
from database.mongodb.config import (
    start_mongo_client,
    stop_mongo_client,
)
from openai_client.config import (
    start_openai_client,
    stop_openai_client,
)
from shared.logging import LogStyle, rich_print


async def start_api_lifecycle():
    """
    Start the API lifecycle by initializing necessary
    clients and loading environment variables.
    """
    rich_print(
        message="Starting Portfolio Backend...",
        style=LogStyle.INFO,
        prefix="[API LIFECYCLE]"
    )
    load_environment_variables()
    await start_mongo_client()
    start_openai_client()

    # Log successful startup
    env = getenv("PORTFOLIO_AGENT_ENV")
    port = getenv("PORTFOLIO_AGENT_PORT")
    rich_print(
        message=(
            f"Portfolio Backend started successfully "
            f"in {env} environment on port {port}."),
        style=LogStyle.INFO,
        prefix="[API LIFECYCLE]"
    )

async def stop_api_lifecycle():
    """Stop the API lifecycle by shutting down clients."""
    rich_print(
        message="Stopping Portfolio Backend...",
        style=LogStyle.INFO,
        prefix="[API LIFECYCLE]"
    )
    await stop_openai_client()
    await stop_mongo_client()

    # Log successful shutdown
    rich_print(
        message="Portfolio Backend stopped successfully.",
        style=LogStyle.INFO,
        prefix="[API LIFECYCLE]"
    )