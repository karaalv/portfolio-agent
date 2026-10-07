from openai.types.responses import ResponseInputParam

from shared.logging import LogStyle, rich_print


def log_agent_history(
	history: ResponseInputParam,
) -> None:
	rich_print('Agent history', LogStyle.INFO)
	for i, entry in enumerate(history):
		rich_print(f'Entry {i}: {entry}', LogStyle.INFO)
