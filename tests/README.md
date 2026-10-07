# Tests

## Structure

- `users/unit/`: mocked user CRUD tests without service clients.
- `users/integration/`: CRUD against the testing MongoDB project.
- `clients/mongodb/connection/`: live ping and collection access.
- `clients/openai/connection/`: authenticated model listing.
- `clients/openai/functionality/`: embeddings, text, structured
  responses, streamed text and streamed function calls.
- `rag/integration/`: index readiness, uploaded corpus and
  query planning, vector retrieval and LLM-judged context.
- `shared/`: reusable fixtures imported by scoped conftests.
- `schemas/`: response models used only by tests.

There is no root server bootstrap. Client fixtures are requested
explicitly, start once per package and close at package teardown.
Async integration tests share their client package event loop.
User-record cleanup remains per test.
Package conftests do not start services during collection.

## Unit tests

No environment file or credentials are required:

```sh
uv run pytest tests/users/unit
```

## Live integration tests

Create `.env.testing` at the repository root. Set its testing
project credentials and the required `MONGODB_URI`, `OPENAI_KEY`,
`JWT_SECRET`, `PORTFOLIO_AGENT_PORT` and `CORS_ORIGINS` values.
Do not select a development or production environment.

```sh
export PORTFOLIO_AGENT_ENV=testing
uv run pytest tests/users/integration
uv run pytest tests/clients/mongodb/connection
uv run pytest tests/clients/openai/connection
uv run pytest tests/clients/openai/functionality
uv run pytest tests/rag/integration
```

The OpenAI connection test lists models. Functionality tests
make real embedding and model requests and consume API usage.
All four current OpenAI wrapper functions are exercised.

User fixtures remove only the identities created by their test.
They do not clear collections. MongoDB connection tests only
read data. Each package fixture closes its client on teardown, including
after test failures.

## RAG integration tests

Bootstrap the testing corpus before running these tests:

```sh
export PORTFOLIO_AGENT_ENV=testing
uv run python -m corpus.bootstrap
uv run pytest tests/rag/integration
```

The readiness checks require a queryable vector index with the
configured path and 3072 dimensions. Every local corpus label
must exist in MongoDB, and stored embeddings must be finite,
non-zero vectors of the expected length. Label coverage does
not verify that uploaded text matches the latest local edits.
Bootstrap skips insertion when the collection already has data.

The quality test asks about Alvin's Imperial MSc and calls the
real planner, vector search and context refiner. A separate
structured model request judges that context against fixed
facts from `corpus/documents/education.md`. It requires the
correct degree, institution, classification and source label.
Failure output includes the verdict explanation and context.
Update the reference if those source facts change.

`test_query_planner.py` checks the live `QueryPlan` structure,
query count and non-empty, distinct searches. An LLM judge
checks their relevance and coverage of the education request.

`test_query_executor.py` calls `_retrieve_query` directly and
requires the expected education entry as a `CorpusItem`, with
embedding data omitted. It also calls `execute_rag` with a fixed
two-query plan and judges the refined context against the same
education facts. This isolates executor quality from planning.

All judge requests use `tests/shared/llm_judge.py`. The helper
accepts system and user prompts and returns an `LLMJudgement`
with `satisfactory` and `reason` fields. Each test owns its rubric
and assertion; model settings and response parsing are shared.

RAG tests share package-scoped MongoDB and OpenAI clients. They
read existing data without creating users, memories or corpus
entries. The quality test uses a fresh user ID for empty history.
It consumes API usage and remains non-deterministic because both
retrieval planning and judging involve language models. Passing
these education cases is smoke coverage, not a broad benchmark.

## Markers

The migrated suites declare `unit` or `integration` markers:

```sh
uv run pytest tests/users tests/clients -m unit
uv run pytest tests/users tests/clients --collect-only
```

Other existing test packages still need migration. API tests
will use HTTPX when the new API contract is implemented.
