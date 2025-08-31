"""
This module contains schemas for
agent tools and tool operations.
"""

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
	"""
	Represents a plan for conducting
	research based on input context
	seed.
	"""

	queries: list[str] = Field(
		...,
		description='A list of queries to be executed '
		'as part of the plan, max 3',
		max_length=3,
	)
