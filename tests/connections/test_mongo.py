"""
This module tests the connection to 
the MongoDB database.
"""
from database.mongodb.config import connect_mongo, close_mongo

# --- Tests ---

async def test_connect_mongo():
    """
    Test the MongoDB connection.
    It should establish a connection and return True.
    """
    assert await connect_mongo(), \
        "Failed to connect to MongoDB."

    assert await close_mongo(), \
        "Failed to close MongoDB connection."