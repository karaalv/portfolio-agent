"""Validate arguments accepted by the context retrieval tool."""

from pydantic import BaseModel, ConfigDict, Field


class FetchContextArguments(BaseModel):
	"""The visitor text used to retrieve portfolio context."""

	model_config = ConfigDict(extra='forbid')
	user_input: str = Field(min_length=1, strict=True)
