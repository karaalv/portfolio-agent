"""
This module is used to create the 
vector search index for the corpus
data in MongoDB.
"""
import asyncio
from pymongo.operations import SearchIndexModel
from database.mongodb.config import connect_mongo, close_mongo
from database.mongodb.main import get_collection

async def _push_index():
    """
    Creates vector search index for corpus 
    collection.
    """
    index_name = "corpus_vector_index"
    collection = get_collection("corpus")
    
    vector_index = SearchIndexModel(
        name=index_name,
        type="vectorSearch",
        definition={
            "fields":[{
                "type": "vector",
                "path": "embedding",
                "numDimensions": 3072,
                "similarity": "cosine"
            }]
        }
    )

    print("⏳ Creating vector search index...")
    await collection.create_search_index(vector_index)

    # NOTE This does not wait till the index is 
    # queryable but just ensures it is created.
    
    waiting = True
    while waiting:
        cursor = await collection.list_search_indexes()
        for i in await cursor.to_list(length=None):
            if i["name"] == index_name:
                waiting = False
                break
            await asyncio.sleep(5)

    print("✅ Vector search index created successfully.")

async def main():
    await connect_mongo()
    await _push_index()
    await close_mongo()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(
        override=True,
        dotenv_path=os.path.abspath(".env")
    )
    
    asyncio.run(main())