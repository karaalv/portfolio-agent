"""
This module contains the conversation
compressor which is used to summarise
the user's conversation history.
"""
from common.utils import handle_exceptions_async
from openai_client.main import normal_response
from agent.memory.main import retrieve_memory
from database.mongodb.main import get_collection

# --- Conversation compression ---

@handle_exceptions_async("agent.memory: Compressing Conversation")
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

    system_prompt = f"""
        You are an expert conversation summarizer for a 
        portfolio website, which features a Retrieval-
        Augmented Generation (RAG) agent to interact with 
        visitors, potential recruiters, and collaborators.

        Your task is to condense the following conversation 
        history into a clear, concise summary that preserves 
        all key details, context, and nuances relevant to the 
        user. The summary will be used for RAG retrieval, so 
        maintain any information that could support accurate 
        inference in future interactions. Avoid unnecessary 
        wording—focus only on essential facts and context.

        The conversation history will be passed in the user
        prompt.
    """

    return await normal_response(
        system_prompt=system_prompt,
        user_input=memory
    )

# --- User Update ---

@handle_exceptions_async("agent.memory: Updating User Summarisation")
async def update_user_summarisation(user_id: str) -> None:
    """
    Update the user's summarisation in the database.
    """
    collection = get_collection("users")
    summary = await compress_conversation(user_id)
    await collection.update_one(
        {"user_id": user_id},
        {"$set": {"conversation_summary": summary}}
    )

# --- Retrieval ---

async def get_user_summarisation(
    user_id: str
) -> str:
    """
    Retrieve the user's summarisation from the DB.
    """
    coll = get_collection("users")
    user = await coll.find_one({"user_id": user_id})
    if not user:
        return ""
    return user.get("conversation_summary", "")
