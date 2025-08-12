"""
This module contains the retriever 
for the RAG system, which executes
the query plan and retrieves relevant
documents from the corpus.
"""
import json
import asyncio
from corpus.schemas import CorpusItem
from rag.schemas import QueryPlan
from database.mongodb.main import get_collection
from openai_client.main import get_embedding

async def retrieve_documents(
    query_plan: QueryPlan
) -> str:
    """
    Retrieve docs from the corpus in parallel 
    based on the query plan. Returns a single 
    concatenated string.

    Args:
        query_plan (QueryPlan): The query plan to 
        execute.

    Returns:
        str: The concatenated string of retrieved 
        document texts.
    """

    retrieval_limit = 1
    collection = get_collection("corpus")
    sem_docs = asyncio.Semaphore(10)
    sem_emb = asyncio.Semaphore(10)
    queries = query_plan.queries

    # Parallel fetch embeddings
    async def embed(query: str) -> list[float]:
        async with sem_emb:
            return await get_embedding(query)

    embeddings = await asyncio.gather(
        *[embed(q) for q in queries]
    )

    # Parallel fetch documents
    async def fetch(query_vector):
        async with sem_docs:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "corpus_vector_index",
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": retrieval_limit * 25,
                        "limit": retrieval_limit,
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "embedding": 0,
                    }
                },
            ]
            cursor = await collection.aggregate(pipeline)
            docs = await cursor.to_list(length=None)

            if not docs:
                return ""
            
            item = CorpusItem(**docs[0])
            return json.dumps(
                {
                    "context": item.context,
                    "document": item.document,
                },
                indent=2
            )

    parts = await asyncio.gather(
        *[fetch(vec) for vec in embeddings]
    )

    return "\n".join(parts)