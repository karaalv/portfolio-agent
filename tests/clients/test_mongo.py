"""Tests for MongoDB client operations."""

from database.mongodb.config import is_mongo_connected


async def test_is_mongo_connected():
    """Test if the MongoDB client is connected."""
    connected = await is_mongo_connected()
    assert isinstance(connected, bool), \
        "Expected a boolean value for connection status."
