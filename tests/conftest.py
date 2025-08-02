"""
Pytest configuration
"""
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(
    override=True,
    dotenv_path=os.path.abspath(".env.test")
)

import pytest
from common.utils import TerminalColors

def pytest_configure():
    """
    Configure pytest, start server 
    and check environment.
    """
    print(
        f"{TerminalColors.yellow}"
        f"Starting portfolio-agent tests...\n"
        f"{TerminalColors.reset}"
    )

    env = os.getenv("ENVIRONMENT")
    if env != "test":
        pytest.exit(
            f"{TerminalColors.red}"
            f"Environment is not set to 'test'. "
            f"Current environment: {env}."
            f"{TerminalColors.reset}"
        )

def pytest_sessionfinish():
    """
    Teardown after all tests are done.
    Closes the MongoDB connection.
    """
    print(
        f"{TerminalColors.yellow}"
        f"\nTest runtime finished."
        f"{TerminalColors.reset}"
    )