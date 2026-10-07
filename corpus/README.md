# RAG Agent Corpus 📚

This folder contains the **RAG Agent Corpus**, a curated collection of documents and resources designed to provide the agent with contextual knowledge for more accurate and relevant responses.

The corpus is used with a **contextual retrieval** approach, enhancing the agent’s ability to recall and apply relevant information during conversations. My implementation follows the general method described in [Anthropic’s article on contextual retrieval](https://www.anthropic.com/news/contextual-retrieval), with custom adaptations for this project.

## Purpose

- Store all written content and reference materials forming the agent’s knowledge base.
- Preprocess, embed, and upload the corpus to MongoDB for retrieval at runtime.
- Serve as the primary source of context for the RAG system during inference.

While this folder is primarily part of the **preprocessing pipeline**, it is included in the repository for completeness and transparency.

## Bootstrapping an environment

Run from the repository root. The corresponding environment
file must exist there:

| Environment | Required file |
| --- | --- |
| `testing` | `.env.testing` |
| `development` | `.env.development` |
| `production` | `.env.production` |

Populate it with `MONGODB_URI`, `OPENAI_KEY`, `JWT_SECRET`,
`PORTFOLIO_AGENT_PORT` and `CORS_ORIGINS`. The command uses the
shared environment loader and its validation rules.

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python -m corpus.bootstrap
```

Replace `development` with `testing` or `production` as needed.
**Run bootstrap in every database environment.** Each has its
own corpus collection and vector search index.

Bootstrap first checks for `corpus_vector_index`, then checks
whether the corpus contains any documents. It independently:

- Creates a missing index and waits until it is queryable.
- Embeds and uploads local corpus files when the collection
  is empty, starting the OpenAI client only for that upload.
- Leaves existing indexes and documents unchanged.

Repeat runs skip resources that already exist. The data check
only tests whether any document exists. It does not detect
partial uploads, reconcile changed files or refresh embeddings.
An existing index is not rebuilt or checked for queryability.

## Individual commands

The original commands remain available:

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python -m corpus.push_corpus
uv run python -m corpus.push_index
```

`push_corpus` uploads file by file. Repeated uploads append
records with fresh IDs and duplicate existing content.

`push_index` creates the named index and waits for queryability.
Creating an index that already exists may fail. Use bootstrap
for conditional initial setup.
