from exceptions.agent import AgentException


def raise_agent_exception(
	message: str,
	module: str,
	operation: str,
) -> None:
	raise AgentException(
		message=message, module=module, operation=operation
	)


def raise_agent_recursion_limit() -> None:
	raise AgentException(
		message='Recursion limit exceeded.',
		module='agent.main',
		operation='agent_chat',
	)
