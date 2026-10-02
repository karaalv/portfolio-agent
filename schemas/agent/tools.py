"""Arguments accepted by the portfolio agent's retrieval tool."""

from pydantic import BaseModel, ConfigDict, Field


class FetchContextArguments(BaseModel):
	"""The visitor's original text, passed to context retrieval."""

	model_config = ConfigDict(extra='forbid')
	user_input: str = Field(min_length=1, strict=True)
