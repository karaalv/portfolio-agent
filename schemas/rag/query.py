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

	agent_thinking_captions: list[str] = Field(
		...,
		description=(
			'Short, visitor-facing retrieval progress captions in '
			'query order, one per query. Describe the topic being '
			'searched without asserting facts or revealing internal '
			'reasoning. Use plain text and at most eight words per '
			'caption. Return an empty list when there are no queries.'
		),
		max_length=MAX_QUERIES,
	)
