"""MongoDB collections for the Portfolio Agent application."""

from enum import StrEnum

# --- MongoDB Database and Collection Enumerations ---


class MongoDBDatabase(StrEnum):
	"""
	Enumeration of MongoDB databases
	for the Portfolio Agent application.
	"""

	APPLICATION = 'application'
	ANALYTICS = 'analytics'


class MongoDBCollection(StrEnum):
	"""
	Enumeration of MongoDB collections
	for the Portfolio Agent application.
	"""

	USERS = 'users'
	MEMORIES = 'memories'
	CORPUS = 'corpus'
	USAGE = 'usage'
	BLOCKED = 'blocked'


# --- Mapping of Collections to Their Databases ---

MONGODB_COLLECTION_TO_DATABASE = {
	# Application Database Collections
	MongoDBCollection.USERS: MongoDBDatabase.APPLICATION,
	MongoDBCollection.MEMORIES: MongoDBDatabase.APPLICATION,
	MongoDBCollection.CORPUS: MongoDBDatabase.APPLICATION,
	# Analytics Database Collections
	MongoDBCollection.USAGE: MongoDBDatabase.ANALYTICS,
	MongoDBCollection.BLOCKED: MongoDBDatabase.ANALYTICS,
}
