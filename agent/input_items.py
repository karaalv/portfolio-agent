"""
Used to define the structure of input items for the agent.
"""

from typing import cast

from openai.types.responses import (
	EasyInputMessageParam,
	ResponseFunctionToolCallParam,
	ResponseInputItemParam,
	ResponseOutputItem,
)
from openai.types.responses.response_input_param import (
	FunctionCallOutput,
)


def response_item_to_input_item(
	item: ResponseOutputItem,
) -> ResponseInputItemParam:
	"""Serialise a completed output item for model replay.

	Preserve SDK fields, including encrypted reasoning and IDs.
	The cast supplies input typing; it does not validate data.
	"""
	return cast(
		ResponseInputItemParam,
		item.model_dump(mode='json', exclude_none=True),
	)


def create_user_input_item(content: str) -> EasyInputMessageParam:
	return {'type': 'message', 'role': 'user', 'content': content}


def create_assistant_input_item(
	content: str,
) -> EasyInputMessageParam:
	return {
		'type': 'message',
		'role': 'assistant',
		'content': content,
	}


def create_function_call_item(
	id: str, call_id: str, tool_name: str, tool_args: str
) -> ResponseFunctionToolCallParam:
	return {
		'id': id,
		'call_id': call_id,
		'type': 'function_call',
		'name': tool_name,
		'arguments': tool_args,
	}


def create_function_output_item(
	call_id: str, tool_result: str
) -> FunctionCallOutput:
	return {
		'type': 'function_call_output',
		'call_id': call_id,
		'output': tool_result,
	}
