"""Coloured terminal output for development and diagnostics."""

from enum import Enum

from rich.console import Console
from rich.theme import Theme


class LogStyle(str, Enum):
	DEFAULT = 'default'
	ERROR = 'error'
	SUCCESS = 'success'
	WARNING = 'warning'
	INFO = 'info'


_theme = Theme(
	{
		'default': 'white',
		'error': 'bold red',
		'success': 'bold green',
		'warning': 'bold yellow',
		'info': 'bold blue',
	}
)

_console = Console(theme=_theme)


def rich_print(
	message: str,
	style: LogStyle = LogStyle.DEFAULT,
	prefix: str | None = None,
) -> None:
	"""Print a message with the selected terminal style."""
	if prefix:
		message = f'[{prefix}] {message}'
	_console.print(message, style=style.value, markup=False)
