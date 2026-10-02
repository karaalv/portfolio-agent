"""
Serialise retrieval results for the model's tool-output messages.
"""
from textwrap import dedent

def format_successful_tool_response(
	tool_name: str, 
	context: str
) -> str:
	return dedent(
		f"""
		The {tool_name} executed successfully.
		Use the following context to continue:
		{context}
		"""
	)


def format_failed_tool_response(message: str) -> str:
	return dedent(
		f"""
		The tool execution failed.
		Reason: {message}
		"""
	)
