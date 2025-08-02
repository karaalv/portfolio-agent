"""
This module contains Pydantic schemas 
for user related information.
"""
from pydantic import BaseModel, Field

class User(BaseModel):
    """
    Represents a user visiting 
    the application.
    """
    user_id: str = Field(
        ...,
        description="Unique identifier for "
                    "the user",
    )
    last_active: str = Field(
        ...,
        description="Timestamp of the user's "
                    "last activity",
    )