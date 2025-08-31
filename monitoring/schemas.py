"""
This module defines Pydantic schemas
for monitoring processes.
"""

from pydantic import BaseModel, Field


class UserUsage(BaseModel):
	user_id: str = Field(..., description='Identifier for the user.')
	usage_id: str = Field(..., description='Identifier for the usage record.')
	ip: str = Field(..., description='IP address of the user.')
	generation_count: int = Field(
		..., description='Number of generations performed.'
	)
	total_generations: int = Field(
		...,
		description='Total number of generations performed.',
	)
	latest_generation: str = Field(
		...,
		description='Timestamp of the latest generation.',
	)
