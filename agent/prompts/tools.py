"""
Format failures for replayable function call outputs.
"""

from textwrap import dedent


def format_failed_tool_response(message: str) -> str:
	"""Explain a failure so the agent can revise its call."""
	return dedent(
		f"""
		The tool execution failed.
		Reason: {message}
		"""
	)


def format_tool_exception_response(
	tool_name: str,
	message: str,
) -> str:
	"""Explain an exception so the agent can revise its call."""
	return dedent(
		f"""
		The tool execution encountered an exception.
		Tool: {tool_name}
		Reason: {message}
		"""
	)
