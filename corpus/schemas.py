"""
This module contains the schemas used 
for RAG Agent Corpus documents.
"""
from pydantic import BaseModel, Field
from typing import Optional

class CorpusItem(BaseModel):
    """
    Represents a single item in the 
    RAG Agent Corpus.
    """
    id: str = Field(
        ...,
        description="The unique identifier for "
                    "the corpus item."
    )
    header: str = Field(
        ...,
        description="The header for the corpus item "
                    "used when streaming chain of thought."
    )
    embedding: Optional[list[float]] = Field(
        None,
        description="The embedding vector for the corpus "
                    "item."
    )
    context: str = Field(
        ...,
        description="The context for the corpus item."
    )
    document: str = Field(
        ...,
        description="The document text for the corpus item."
    )