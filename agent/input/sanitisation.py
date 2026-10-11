"""Clean obvious input noise without redacting personal data."""

import re
import unicodedata

from agent.config.input import (
	MAX_INPUT_LENGTH,
	MAX_SINGLE_INPUT_TOKEN_LENGTH,
)

_LONG_TOKEN = re.compile(
	rf'\S{{{MAX_SINGLE_INPUT_TOKEN_LENGTH + 1},}}'
)
_REPETITION = re.compile(r'(.)\1{19,}')
_SPACING = re.compile(r'[ \t]+')
_BLANK_LINES = re.compile(r'\n{3,}')


def sanitise_input(value: str) -> str:
	"""Normalise text, remove obvious noise and cap its length.

	Preserve names, non-English text, URLs and personal details.
	Return empty text when cleaning removes all useful content.
	"""
	text = unicodedata.normalize('NFKC', value)
	text = text.replace('\r\n', '\n').replace('\r', '\n')
	text = ''.join(
		character
		for character in text
		if character in ('\n', '\t', '\u200c', '\u200d')
		or not unicodedata.category(character).startswith('C')
	)
	text = _LONG_TOKEN.sub('', text)
	text = _REPETITION.sub('', text)
	text = _SPACING.sub(' ', text)
	text = _BLANK_LINES.sub('\n\n', text).strip()
	compact = ''.join(text.split())
	if len(compact) > 20 and not any(
		character.isalnum() for character in compact
	):
		return ''
	return text[:MAX_INPUT_LENGTH].strip()
