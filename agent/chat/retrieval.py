"""Retrieve frontend messages from stored model items."""

from typing import TypeGuard

from openai.types.responses import (
	EasyInputMessageParam,
	ResponseInputItemParam,
	ResponseOutputMessageParam,
)
from openai.types.responses.response_input_param import Message

from agent.config.memory import AGENT_MEMORY_PAGE_SIZE
from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.chat import AgentChatMemory, AgentChatSource
from schemas.agent.memory import AgentMemory

ChatMessagePayload = (
	EasyInputMessageParam | Message | ResponseOutputMessageParam
)


async def retrieve_agent_chat_page(
	user_id: str, offset: int
) -> list[AgentChatMemory]:
	"""Return a chronological page of visitor and agent messages.

	Offset counts visible messages from the newest message.
	Prepend older pages to the chat. Tool and reasoning items
	are excluded before pagination and never sent to the client.
	"""
	if offset < 0:
		raise ValueError('The chat offset must not be negative.')

	collection = get_collection(MongoDBCollection.MEMORIES)
	cursor = (
		collection.find(
			{
				'user_id': user_id,
				'payload.type': 'message',
				'payload.role': {'$in': ['user', 'assistant']},
			},
			{'_id': 0},
		)
		.sort([('created_at', -1), ('sequence', -1)])
		.skip(offset)
		.limit(AGENT_MEMORY_PAGE_SIZE)
	)
	messages = [
		_to_agent_chat_memory(AgentMemory.model_validate(document))
		async for document in cursor
	]
	messages.reverse()
	return messages


def _to_agent_chat_memory(
	memory: AgentMemory,
) -> AgentChatMemory:
	"""Convert one stored message into frontend text."""
	payload = memory.payload
	if not _is_chat_message(payload):
		raise ValueError('Memory must contain a chat message.')

	content = payload['content']
	if isinstance(content, str):
		text = content
	else:
		parts: list[str] = []
		for block in content:
			if block['type'] in {'input_text', 'output_text'}:
				parts.append(block.get('text', ''))
			elif block['type'] == 'refusal':
				parts.append(block['refusal'])
		text = ''.join(parts)

	return AgentChatMemory(
		memory_id=memory.memory_id,
		user_id=memory.user_id,
		created_at=memory.created_at,
		memory_source=(
			AgentChatSource.USER
			if payload['role'] == 'user'
			else AgentChatSource.AGENT
		),
		content=text,
	)


def _is_chat_message(
	payload: ResponseInputItemParam,
) -> TypeGuard[ChatMessagePayload]:
	"""Identify visitor and assistant message payloads."""
	return payload.get('type') == 'message' and payload.get(
		'role'
	) in {'user', 'assistant'}
