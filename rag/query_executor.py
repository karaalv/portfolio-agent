"""
This module contains the retriever 
for the RAG system, which executes
the query plan and retrieves relevant
documents from the corpus.
"""
import textwrap
import json
import asyncio
from corpus.schemas import CorpusItem
from rag.schemas import QueryPlan
from common.utils import handle_exceptions_async, TerminalColors
from database.mongodb.main import get_collection
from openai_client.main import get_embedding, normal_response
from api.common.socket_registry import send_message_ws

# --- Constants ---

_refiner_model = "gpt-4.1-mini"

# --- Utils ---

def _package_item(item: CorpusItem) -> str:
    """
    Package a CorpusItem into a JSON string
    with relevant information.
    """
    return json.dumps(
        {
            "context": item.context,
            "document": item.document,
        },
        indent=2
    )

# --- Retriever ---

@handle_exceptions_async("rag.query_executor: Retrieve Documents Sequential")
async def retrieve_documents_sequential(
    user_id: str,
    query_plan: QueryPlan,
    verbose: bool = False
) -> str:
    """
    Retrieve docs from corpus in sequential
    manner:

    Args:
        user_id (str): The ID of the user making the 
        request.
        query_plan (QueryPlan): The query plan to
        execute.
        verbose (bool): Whether to print verbose output.

    Returns:
        str: The concatenated string of retrieved
        document texts.
    """
    retrieval_limit = 3
    retrieval_threshold = 0.6
    collection = get_collection("corpus")
    queries = query_plan.queries

    results: list[str] = []
    for query in queries:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "corpus_vector_index",
                    "path": "embedding",
                    "queryVector": await get_embedding(query),
                    "numCandidates": retrieval_limit * 25,
                    "limit": retrieval_limit,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "embedding": 0,
                    'score': {
                        '$meta': 'vectorSearchScore'
                    }
                }
            },
            {
                "$match": {
                    "score": {
                        "$gt": retrieval_threshold
                    }
                }
            },
            {
                "$project": {
                    "score": 0
                }
            },
        ]
        
        cursor = await collection.aggregate(pipeline)
        docs = await cursor.to_list(length=None)

        if not docs:
            continue

        items = [CorpusItem(**doc) for doc in docs]
        headers = [item.header for item in items]
        items_str = "\n".join(
            item.model_dump_json(indent=2) for item in items
        )

        # Send headers to client
        await send_message_ws(
            user_id=user_id,
            type="agent_thinking",
            data=headers
        )

        item_results = [_package_item(item) for item in items]

        if verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Retrieved document for query: {query}"
                f"{TerminalColors.reset}"
            )
            print(items_str)

        results.append('\n'.join(item_results))

    return "\n".join(results)

# TODO parallel approach has race condition on result
# implement a locking mechanism or use a more robust data structure

@handle_exceptions_async("rag.query_executor: Retrieve Documents Parallel")
async def _retrieve_documents_parallel(
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

# --- Augmenter: Context Refiner ---

@handle_exceptions_async("rag.query_executor: Refine Context")
async def refine_context(
    user_input: str,
    retrieval_results: str
) -> str:
    """
    Refines the context of the retrieved documents
    using the context of the refined user input to
    synthesise coherent context before generation.

    Args:
        refined_input (str): The refined user 
        input.
        retrieval_results (str): The retrieved document 
        contexts.

    Returns:
        str: The refined context.
    """
    system_prompt = textwrap.dedent(f"""
        You are an expert context augmenter for a portfolio
        site with a Retrieval-Augmented Generation (RAG)
        agent.

        Task:
        - First, repeat the user's original input verbatim.
        - Then, produce a single, coherent Augmented Context
        using only relevant info from retrieval.
        - Rephrase the context in present tense and first
        person (e.g., "I am...", "I work on...", "I have
        experience in...") so it reads as if I am speaking.
        - When referring to information from the retrieved
        documents, make sure to cite the full context that
        supports your statements to support your claims.

        Goals:
        - Preserve the user's intent and constraints.
        - Select only relevant info; drop noise and fluff.
        - Merge overlaps; deduplicate; normalise terms.
        - Resolve conflicts without inventing new facts.
        - Prefer recent or specific info when entries differ.
        - Do not provide multiple options or extra commentary.

        Method:
        - Treat retrieved context and documents as related
        units.
        - Extract key facts, entities, dates, and definitions
        that support the task.
        - If uncertainty remains, state it briefly and move on.

        Output (exactly two sections):
        1) "User Input:"
        - The original user input, verbatim.
        2) "Augmented Context:"
        - A concise, first-person, present-tense unified
            context suitable for generation.

        Inputs:
        - Original user input: provided in the user message.
        - Retrieved entries:
        {retrieval_results}
    """)

    return await normal_response(
        system_prompt=system_prompt,
        user_input=user_input,
        model=_refiner_model
    )