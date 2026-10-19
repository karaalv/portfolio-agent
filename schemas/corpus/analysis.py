"""Define corpus item and document token-count summaries."""

from pydantic import BaseModel


class CorpusItemAnalysis(BaseModel):
	"""Token counts for one labelled corpus section."""

	item_label: str
	context_token_count: int
	document_token_count: int
	total_token_count: int


class CorpusDocumentAnalysis(BaseModel):
	"""Section summaries and the total for a corpus file."""

	file_label: str
	section_count: int
	total_token_count: int
	corpus_items: list[CorpusItemAnalysis]
