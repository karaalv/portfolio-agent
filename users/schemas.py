"""
This module contains Pydantic schemas
for user related information.
"""

from pydantic import BaseModel, Field

from common.utils import get_timestamp


class User(BaseModel):
	"""
	Represents a user visiting
	the application.
	"""

	user_id: str = Field(
		...,
		description='Unique identifier for the user',
	)
	last_active: str = Field(
		...,
		description="Timestamp of the user's last activity",
	)
	created_at: str = Field(
		default_factory=get_timestamp,
		description='Timestamp of when the user was created',
	)
	conversation_summary: str = Field(
		...,
		description="Summary of the user's conversation",
	)
