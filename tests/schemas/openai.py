"""Deterministic response schemas used by OpenAI client tests."""

from typing import Literal

from pydantic import BaseModel


class CapitalResponse(BaseModel):
	"""Structured answer to the fixed geography test prompt."""

	country: Literal['France']
	capital: Literal['Paris']
