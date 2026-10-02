"""Store visitor and assistant messages in MongoDB."""

from database.mongodb import get_collection
from database.mongodb.collections import MongoDBCollection
from schemas.agent.memory import AgentMemory, AgentMemorySource


async def insert_agent_memory(
    user_id: str,
    memory_id: str,
    memory_source: AgentMemorySource,
    content: str
) -> AgentMemory:
    """
    Create and persist one conversation entry,
    returning its model.
    """
    memory = AgentMemory(
        user_id=user_id,
        memory_id=memory_id,
        memory_source=memory_source,
        content=content,
    )
    collection = get_collection(MongoDBCollection.MEMORIES)
    await collection.insert_one(memory.model_dump(mode="json"))
    return memory
