"""
This module contains schemas for
RAG operations.
"""

from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
	"""
	Represents a plan for executing a
	query in the RAG system.
	"""

	queries: list[str] = Field(
		...,
		description='A list of queries to be executed '
		'as part of the plan, max 3',
		max_length=3,
	)
