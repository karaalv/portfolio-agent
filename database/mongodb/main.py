"""
This module acts as the main 
entry point for MongoDB operations.
"""
from pymongo.asynchronous.collection import AsyncCollection
from database.mongodb.config import (
    get_mongo_client, 
    database_mappings,
    COLLECTIONS
)

# --- Resource Resolvers ---

def get_collection(
    collection_name: str
) -> AsyncCollection:
    """
    Retrieves a collection from 
    MongoDB, resolves the database
    during the process.

    Args:
        collection_name (str): The name of the collection
                              to retrieve.
    
    Returns:
        AsyncCollection: The collection object.
    """
    client = get_mongo_client()

    if not client:
        raise ConnectionError(
            "MongoDB client is not connected."
        )
    
    if collection_name not in COLLECTIONS:
        raise ValueError(
            f"Collection '{collection_name}' "
            " is not registered in the system."
        )
    
    db = database_mappings.get(collection_name)

    if not db:
        raise ValueError(
            f"Database mapping for collection "
            f"'{collection_name}' not found."
        )
    
    return client[db][collection_name]