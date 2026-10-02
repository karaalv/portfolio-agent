"""
Define portfolio corpus entries
used for context retrieval.
"""

from pydantic import BaseModel


class CorpusItem(BaseModel):
	"""
	One knowledge-base entry and
	its context embedding.
	"""

	item_id: str
	label: str
	header: str
	embedding: list[float]
	context: str
	document: str
