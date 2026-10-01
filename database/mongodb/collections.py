"""MongoDB collections for the Portfolio Agent application."""

from enum import Enum

# --- MongoDB Database and Collection Enumerations ---

class MongoDBDatabase(str, Enum):
    """
    Enumeration of MongoDB databases 
    for the Portfolio Agent application.
    """
    APPLICATION = "application"
    ANALYTICS = "analytics"

class MongoDBCollection(str, Enum):
    """
    Enumeration of MongoDB collections 
    for the Portfolio Agent application.
    """
    USERS = "users"
    MESSAGES = "messages"
    CORPUS = "corpus"
    MONITORING = "monitoring"

# --- Mapping of Collections to Their Databases ---

MONGODB_COLLECTION_TO_DATABASE = {
    # Application Database Collections
    MongoDBCollection.USERS: MongoDBDatabase.APPLICATION,
    MongoDBCollection.MESSAGES: MongoDBDatabase.APPLICATION,
    MongoDBCollection.CORPUS: MongoDBDatabase.APPLICATION,
    # Analytics Database Collections
    MongoDBCollection.MONITORING: MongoDBDatabase.ANALYTICS,
}

