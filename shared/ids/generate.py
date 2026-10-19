"""Generate random UUID identifiers."""

from uuid import uuid4


def generate_uuid_str() -> str:
	"""Return a random UUID version 4 as a canonical string."""
	return str(uuid4())
