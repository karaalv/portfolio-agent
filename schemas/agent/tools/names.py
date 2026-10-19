"""Canonical names shared by tool definitions and dispatch."""

from enum import StrEnum


class AgentToolName(StrEnum):
	"""Functions available to the portfolio agent."""

	FETCH_CONTEXT = 'fetch_context'
