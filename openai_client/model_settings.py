"""
Module for managing OpenAI model settings.
"""

from enum import StrEnum


class OpenAILanguageModelReasoning(StrEnum):
	LOW = 'low'
	MEDIUM = 'medium'
	HIGH = 'high'

class OpenAILanguageModelVerbosity(StrEnum):
	LOW = 'low'
	MEDIUM = 'medium'
	HIGH = 'high'