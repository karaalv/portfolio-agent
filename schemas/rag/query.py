"""Define semantic queries for corpus context retrieval."""

from pydantic import BaseModel, Field

from rag.config import MAX_QUERIES


class QueryPlan(BaseModel):
	"""Distinct semantic searches for a visitor request."""

	queries: list[str] = Field(
		...,
		description=(
			'Focused, self-contained semantic searches about '
			'Alvin Karanja. Each query covers a distinct aspect '
			'of the request without assuming unverified facts. '
			'Use at most three queries; an empty list means '
			'no portfolio information is needed.'
		),
		max_length=MAX_QUERIES,
	)
