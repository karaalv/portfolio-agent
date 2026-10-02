# RAG Agent Corpus 📚

This folder contains the **RAG Agent Corpus**, a curated collection of documents and resources designed to provide the agent with contextual knowledge for more accurate and relevant responses.  

The corpus is used with a **contextual retrieval** approach, enhancing the agent’s ability to recall and apply relevant information during conversations. My implementation follows the general method described in [Anthropic’s article on contextual retrieval](https://www.anthropic.com/news/contextual-retrieval), with custom adaptations for this project.  

## Purpose

- Store all written content and reference materials forming the agent’s knowledge base.  
- Preprocess, embed, and upload the corpus to MongoDB for retrieval at runtime.  
- Serve as the primary source of context for the RAG system during inference.  

While this folder is primarily part of the **preprocessing pipeline**, it is included in the repository for completeness and transparency.

## Uploading the corpus and creating the index

Run these commands from the repository root. The corresponding
**environment file must exist** in the repository root:

| Environment | Required file |
| --- | --- |
| `testing` | `.env.testing` |
| `development` | `.env.development` |
| `production` | `.env.production` |

Populate the file with the target environment's settings,
including its `MONGODB_URI` and `OPENAI_KEY`. Both scripts use
the shared environment loader, which also requires valid
`PORTFOLIO_AGENT_PORT` and `CORS_ORIGINS` values.

Select the environment, then upload the corpus and create its
vector search index:

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python -m corpus.push_corpus
uv run python -m corpus.push_index
```

Replace `development` with `testing` or `production` as needed.
**Perform both steps in every database environment.** Each
MongoDB environment has its own corpus collection and search
index; setting up one does not configure the others.

`push_corpus` generates embeddings and inserts records file by
file. Repeat uploads append records with fresh IDs and duplicate
existing content.

`push_index` creates `corpus_vector_index` and waits until it is
queryable. Run it when setting up the index; rerunning creation
against an existing index may fail.
