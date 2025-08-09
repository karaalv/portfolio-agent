"""
Main interface for agent
memory management
"""
import json
from agent.memory.schemas import AgentMemory, AgentCanvas
from common.utils import handle_exceptions_async, get_timestamp
from database.mongodb.main import get_collection

# --- Creation ---

@handle_exceptions_async("agent.memory: Pushing Agent Memory")
async def push_memory(
    user_id: str,
    source: str,
    content: str
) -> None:
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
        id=f"{user_id}_{source}_{get_timestamp()}",
        user_id=user_id,
        source=source,
        content=content
    )

    collection = get_collection("messages")
    await collection.insert_one(memory.model_dump())
    
    return None

# --- Retrieval ---

@handle_exceptions_async("agent.memory: Retrieving Agent Memory")
async def retrieve_memory( 
    user_id: str, 
    to_str: bool = False
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
    collection = get_collection("messages")

    cursor = collection.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("serverCreatedAt", 1)

    data = await cursor.to_list(length=None)
    results = [AgentMemory(**item) for item in data]

    if to_str:
        return json.dumps([
            memory.model_dump() for memory in results], 
            indent=2
        )

    return results

# --- Deletion ---

@handle_exceptions_async("agent.memory: Deleting chat history")
async def delete_memory(
    user_id: str
) -> bool:
    """
    Deletes all agent memory for a specific user.

    Args:
        user_id: The unique identifier for the user
    """
    collection = get_collection("messages")
    result = await collection.delete_many({"user_id": user_id})

    if result.deleted_count > 0:
        return True

    return False