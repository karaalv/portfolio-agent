"""
This module contains the conversation
compressor which is used to summarise
the user's conversation history.
"""

import textwrap

from agent.memory.main import retrieve_memory
from common.utils import handle_exceptions_async
from database.mongodb.main import get_collection
from openai_client.main import normal_response

# --- Constants ---

compression_model = 'gpt-4.1-mini'

# --- Conversation compression ---


@handle_exceptions_async('agent.memory: Compressing Conversation')
async def compress_conversation(
	user_id: str,
) -> str:
	"""
	Compress the user's conversation history
	into a summary using LLM as a judge.

	Args:
		user_id (str): The unique identifier for the user.
	"""

	memory = await retrieve_memory(user_id, to_str=True)

	system_prompt = textwrap.dedent("""
        You are an expert conversation summarizer for a portfolio
        sites RAG agent, which interacts as me—Alvin Karanja.

        Your job is to condense the following chat history into a
        clear and concise summary, written in first person to
        sound like me ("I worked on...", "I discussed..."), while
        retaining all key details, intent, and context that
        matter for retrieval accuracy.

        Key rules:
        - Use first person present or past tense to match the
        persona (e.g., "I explored...", "I learned...").
        - Preserve user intent and conversation nuance.
        - Keep the summary focused: no filler, no assumptions.
        - Ensure it supports accurate inference in future
        RAG retrieval.
        - Make it as short as possible while remaining
        context-rich.

        The conversation history follows in the user message.
    """)

	return await normal_response(
		system_prompt=system_prompt,
		user_input=memory,
		model=compression_model,
	)


# --- User Update ---


@handle_exceptions_async('agent.memory: Updating User Summarisation')
async def update_user_summarisation(user_id: str) -> None:
	"""
	Update the user's summarisation in the database.
	"""
	collection = get_collection('users')
	summary = await compress_conversation(user_id)
	await collection.update_one(
		{'user_id': user_id},
		{'$set': {'conversation_summary': summary}},
	)


# --- Retrieval ---


async def get_user_summarisation(user_id: str) -> str:
	"""
	Retrieve the user's summarisation from the DB.
	"""
	coll = get_collection('users')
	user = await coll.find_one({'user_id': user_id})
	if not user:
		return ''
	return user.get('conversation_summary', '')
