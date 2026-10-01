"""
Models for interacting with the OpenAI API.
"""

from enum import StrEnum


class OpenAIEmbeddingModel(StrEnum):
    """
    Enumeration of OpenAI embedding models.
    """
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"


class OpenAILanguageModel(StrEnum):
    """
    Enumeration of OpenAI LLM models.
    """
    GPT_6_1_SOL = "gpt-6.1-sol"
    GPT_6_LUNA = "gpt-6-luna"
