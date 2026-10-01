"""
Module for managing OpenAI model settings.
"""

from enum import Enum


class OpenAILanguageModelReasoning(str, Enum):
	LOW = 'low'
	MEDIUM = 'medium'
	HIGH = 'high'

class OpenAILanguageModelVerbosity(str, Enum):
	LOW = 'low'
	MEDIUM = 'medium'
	HIGH = 'high'