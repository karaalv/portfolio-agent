"""Check input cleaning without guessing language or identity."""

import pytest

from agent.config.input import MAX_INPUT_LENGTH
from agent.input.sanitisation import sanitise_input


@pytest.mark.parametrize(
	'value, expected',
	[
		(
			'  Hello\t  Alvin\r\n\r\n\r\nHi\x00 ',
			'Hello Alvin\n\nHi',
		),
		('Ｈｅｌｌｏ', 'Hello'),
		(
			'Habari, Шыңғыс! 你好 👩\u200d💻',
			'Habari, Шыңғыс! 你好 👩\u200d💻',
		),
		(
			'Contact me at a@example.com or https://example.com',
			'Contact me at a@example.com or https://example.com',
		),
		('x' * 50, ''),
		('Hello ' + 'ab' * 51 + ' Alvin', 'Hello Alvin'),
		(' ' * 20, ''),
		('!@#$' * 10, ''),
	],
)
def test_sanitise_input(value: str, expected: str) -> None:
	"""Clean obvious noise while preserving ordinary text."""
	assert sanitise_input(value) == expected


def test_single_token_boundary() -> None:
	"""Keep a 100-character chunk and remove a longer chunk."""
	assert sanitise_input('ab' * 50) == 'ab' * 50
	assert sanitise_input('ab' * 50 + 'c') == ''


def test_input_is_truncated() -> None:
	"""Cap cleaned input without rejecting ordinary long text."""
	value = 'word ' * 600
	assert (
		sanitise_input(value) == value[:MAX_INPUT_LENGTH].strip()
	)
