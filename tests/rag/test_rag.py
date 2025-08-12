"""
This module contains tests for the 
RAG system.
"""
import pytest
from common.utils import TerminalColors
from database.mongodb.config import connect_mongo, close_mongo
from rag.main import fetch_context

# --- Constants ---

TEST_USER_ID = "test_user"
TEST_INPUT = "what makes you a good developer?"

# --- Config ---

@pytest.fixture(scope="function", autouse=True)
async def mongo_session():
    if not await connect_mongo():
        pytest.exit(
            f"{TerminalColors.red}"
            f"Failed to connect to MongoDB."
            f"{TerminalColors.reset}"
        )
    yield
    if not await close_mongo():
        pytest.exit(
            f"{TerminalColors.red}"
            f"Failed to close MongoDB connection."
            f"{TerminalColors.reset}"
        )

# --- Tests ---

async def test_fetch_context():
    """
    Test fetching contextual information
    via the RAG system.
    """
    context = await fetch_context(
        user_id=TEST_USER_ID,
        user_input=TEST_INPUT,
        verbose=True
    )
    assert context is not None, "Expected non-null context"