# Tests

## Structure

- `users/unit/`: mocked user CRUD tests without service clients.
- `users/integration/`: CRUD against the testing MongoDB project.
- `clients/mongodb/connection/`: live ping and collection access.
- `clients/openai/connection/`: authenticated model listing.
- `clients/openai/functionality/`: embeddings, text, structured
  responses, streamed text and streamed function calls.
- `agent/unit/<scope>/`: streaming state, memory, chat and tools.
- `agent/integration/<scope>/`: memory, chat, tools and main loop.
- `agent/agent_input.py`: interactive terminal runner, not a test.
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
uv run pytest tests/agent/unit
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

## Agent tests

```sh
uv run pytest tests/agent/unit
export PORTFOLIO_AGENT_ENV=testing
uv run pytest tests/agent/integration
```

The agent integration package shares MongoDB and OpenAI clients
across its scope folders. Each test gets unique visitor IDs and
removes only its own memories and user records during teardown.
Memory and chat checks use real MongoDB without model requests.
Tool and main-loop tests also require the bootstrapped corpus.

Memory supports creation, insertion, retrieval and deletion.
Chat is a read projection over the same stored artefacts, so
its creation and deletion checks use memory writes. There is
no memory or chat update operation to exercise at present.

Pagination checks advance offsets until the final empty page.
They verify chronological order, complete coverage, no duplicate
IDs, timestamp ties and isolation from other visitors. Chat
pages count visible messages, excluding tool and reasoning items.
History checks retain all artefacts from the selected user-turn
boundary, including the default twenty-turn window.

The dispatcher deliberately returns recoverable error text for
unknown names and invalid arguments. Unit tests check those
responses, backend failures, parallel execution and ordered
`function_call_output` results with matching `call_id` values.

Live main-loop tests exercise a greeting without retrieval and
an education request requiring the context tool. Stream observers
forward real SDK events and record input/output snapshots. Tests
compare these with stored artefacts, checking replayed history,
unique memory IDs, one turn ID, contiguous sequences, tool-output
pairing, stream closure before recursion and final assistant text.
The education response is evaluated using the shared LLM judge.
These live model checks remain non-deterministic and cost usage.

### Interactive terminal session

```sh
export PORTFOLIO_AGENT_ENV=testing
uv run python -m tests.agent.agent_input --verbosity 1
```

Verbosity defaults to 1. Use 0 for minimal agent diagnostics or 2
for SDK event diagnostics. Text deltas are displayed as they
arrive. The runner observes the SDK stream until application
publishing is implemented; production code is unchanged.

The corresponding root environment file must exist. Clients
start before interaction and close on exit or failure. Enter
`exit`, `quit` or Ctrl-D to finish; Ctrl-C cancels the session.
A new visitor is created by default and its records are retained
for inspection. Reuse the printed ID with `--user-id <id>` to
continue that conversation. Bootstrap the corpus before asking
questions requiring portfolio retrieval.

## Markers

The migrated suites declare `unit` or `integration` markers:

```sh
uv run pytest tests/users tests/clients -m unit
uv run pytest tests/users tests/clients --collect-only
```

Other existing test packages still need migration. API tests
will use HTTPX when the new API contract is implemented.
