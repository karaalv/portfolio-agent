"""Print agent history and timing summaries for diagnostics."""

from openai.types.responses import ResponseInputParam

from agent.observability import AgentTimer
from shared.logging import LogStyle, rich_print


def log_agent_history(
	history: ResponseInputParam,
) -> None:
	rich_print('Agent history', LogStyle.INFO)
	for i, entry in enumerate(history):
		rich_print(f'Entry {i}: {entry}', LogStyle.INFO)


def log_agent_timing(timer: AgentTimer) -> None:
	"""Print recorded spans without exposing request content."""
	rich_print('Agent timing', LogStyle.INFO)
	for record in timer.records:
		rich_print(
			f'{record.scope}: {record.name}, '
			f'{record.duration_seconds:.2f}s ({record.status})',
			LogStyle.INFO,
		)
