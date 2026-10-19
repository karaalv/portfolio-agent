"""Describe source files used in corpus processing."""

from pathlib import Path

from pydantic import BaseModel, Field


class CorpusFile(BaseModel):
	"""A corpus source path and its display label."""

	file_path: Path = Field(description='Corpus source path.')
	label: str = Field(description='Display label for the file.')
