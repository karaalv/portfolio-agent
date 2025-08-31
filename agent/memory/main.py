"""
Main interface for agent
memory management
"""

import json
from typing import Literal, overload

from agent.memory.schemas import AgentCanvas, AgentMemory
from common.utils import (
	get_timestamp,
	handle_exceptions_async,
)
from database.mongodb.main import get_collection

# --- Creation ---


@handle_exceptions_async('agent.memory: Pushing Agent Memory')
async def push_memory(user_id: str, source: str, content: str):
	"""
	Pushes agent memory to the database, note this
	is explicitly for instances without canvas
	content

	Args:
		user_id: The unique identifier for the user
		source: The source of the memory (user | agent)
		content: The content of the memory
	"""

	# Package memory
	memory = AgentMemory(
		id=f'{user_id}_{source}_{get_timestamp()}',
		user_id=user_id,
		source=source,
		content=content,
		illusion=False,
	)

	collection = get_collection('messages')
	await collection.insert_one(memory.model_dump())

	return None


@handle_exceptions_async('agent.memory: Pushing Canvas Memory')
async def push_canvas_memory(
	user_id: str,
	title: str,
	agent_response: str,
	canvas_content: str,
):
	"""
	Pushes canvas memory to the database.

	Args:
		user_id: The unique identifier for the user
		agent_memory: The agent memory content
		canvas_content: The canvas content
	"""

	# Package canvas memory
	canvas_memory = AgentCanvas(
		title=title,
		id=f'{user_id}_canvas_{get_timestamp()}',
		content=canvas_content,
	)

	# Package agent memory
	agent_memory = AgentMemory(
		id=f'{user_id}_agent_{get_timestamp()}',
		user_id=user_id,
		source='agent',
		content=agent_response,
		illusion=False,
		agent_canvas=canvas_memory,
	)

	collection = get_collection('messages')
	await collection.insert_one(agent_memory.model_dump())

	return None


# --- Retrieval ---


@overload
async def retrieve_memory(
	user_id: str,
	to_str: Literal[True],
	drop_canvas: bool = False,
) -> str: ...


@overload
async def retrieve_memory(
	user_id: str,
	to_str: Literal[False],
	drop_canvas: bool = False,
) -> list[AgentMemory]: ...


@handle_exceptions_async('agent.memory: Retrieving Agent Memory')
async def retrieve_memory(
	user_id: str,
	to_str: bool = False,
	drop_canvas: bool = False,
) -> list[AgentMemory] | str:
	"""
	Retrieves agent memory from the database.

	Args:
		user_id: The unique identifier for the user
		to_str: Whether to return the memory in JSON
		string format

	Returns:
		A list of AgentMemory objects
	"""
	collection = get_collection('messages')

	cursor = collection.find({'user_id': user_id}, {'_id': 0}).sort(
		'created_at', 1
	)

	data = await cursor.to_list(length=None)
	results = [AgentMemory(**item) for item in data]

	if drop_canvas:
		for r in results:
			if r.agent_canvas:
				r.agent_canvas = None

	if to_str:
		return json.dumps(
			[memory.model_dump() for memory in results],
			indent=2,
		)

	return results


# --- Deletion ---


@handle_exceptions_async('agent.memory: Deleting chat history')
async def delete_memory(user_id: str) -> bool:
	"""
	Deletes all agent memory for a specific user.

	Args:
		user_id: The unique identifier for the user
	"""
	collection = get_collection('messages')

	# Move messages for analysis
	pipeline = [
		{'$match': {'user_id': user_id}},
		{'$out': {'db': 'analysis', 'coll': 'messages'}},
	]
	cursor = await collection.aggregate(pipeline)
	await cursor.to_list(length=None)

	# Delete original messages
	result = await collection.delete_many({'user_id': user_id})

	# Clear user summarisation
	collection = get_collection('users')
	await collection.update_one(
		{'user_id': user_id},
		{'$unset': {'conversation_summary': ''}},
	)

	if result.deleted_count > 0:
		return True

	return False
