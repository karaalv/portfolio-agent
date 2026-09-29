"""Format exception details for diagnostic output."""

import traceback


def format_exception(exc: BaseException) -> str:
	"""Return the exception, its causes, and traceback as text."""
	lines = [f'type={type(exc)!r}', f'repr={exc!r}']

	if exc.__cause__ is not None:
		lines.extend(
			(
				f'cause_type={type(exc.__cause__)!r}',
				f'cause_repr={exc.__cause__!r}',
			)
		)

	if exc.__context__ is not None:
		lines.extend(
			(
				f'context_type={type(exc.__context__)!r}',
				f'context_repr={exc.__context__!r}',
			)
		)

	lines.append('traceback:')
	lines.append(''.join(traceback.format_exception(exc)).rstrip())
	return '\n'.join(lines)
