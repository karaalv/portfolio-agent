# Portfolio Agent v2

Version 2 of my portfolio assistant, built to answer questions
about my background, projects, skills and work through retrieval
augmented generation (RAG). It speaks as an assistant on my
behalf and grounds its answers in the portfolio corpus.

The v2 backend uses FastAPI, the OpenAI Responses API and MongoDB.
It streams plain-text answers over WebSockets, uses a single
`fetch_context` tool for retrieval, and keeps conversation history
as ordered model response artefacts. The RAG planner also produces
short progress captions for the frontend's thinking indicator.

Visitors are anonymous, with JWT access tokens identifying their
conversations. The API includes cookie claiming, chat history
pagination, memory deletion, rate limiting and usage-based
blocking. Background routines maintain security records and
remove user data after seven days of inactivity.

Portfolio: [alvinkaranja.dev](https://www.alvinkaranja.dev/).

## Local setup

Use Python 3.14 and uv. Run all commands from the repository root.
Dependencies follow the `uv pip` workflow: `requirements.in`
contains direct dependencies and `requirements.txt` contains the
resolved versions.
This repository does not use `uv.lock`.

```sh
uv python install 3.14
uv venv --python 3.14
uv pip compile --python .venv/bin/python requirements.in -o requirements.txt --cache-dir .uv/cache
uv pip sync --python .venv/bin/python requirements.txt --cache-dir .uv/cache
```

### Application logging

Use the shared helpers for application logs:

```python
from shared.logging import log_error, log_info

log_info('Maintenance completed', {'deleted_count': 3})

try:
	perform_operation()
except Exception as exc:
	log_error('Operation failed', {'operation': 'example'}, exc=exc)
```

Helpers are available for DEBUG, INFO, WARNING, ERROR and CRITICAL.
The `portfolio_agent` logger writes INFO and above to the terminal.
ERROR and CRITICAL accept an optional `exc` to retain the traceback.
Pass typed attributes through `extra`, avoiding Python's reserved log
record keys such as `message`, `name` and `levelname`.

In development and production, PostHog startup attaches one batched
OpenTelemetry handler to this logger. Logs go to
`POSTHOG_HOST/i/v1/logs` with `POSTHOG_API_KEY` authentication.
Shutdown detaches the handler and drains the provider in a thread.
Testing keeps local logging but never creates the remote exporter.
Existing `rich_print` output and module loggers are not automatically
exported; use the shared helpers for application logs sent to PostHog.

HTTP handlers now log and capture failures with request/session context
and server-resolved user identity. Application exceptions return 500;
HTTP 4xx failures are warnings and 5xx/unexpected failures are errors.
Application startup failures are critical and carry a UTC timestamp.
`WebSocketConnectionException` has a registered handler for handshake,
identity and chat-loop failures; connection workers, maintenance tasks
and swallowed tool exceptions report at their local boundaries.

Every operational record has a stable `event_name`; user/session logs
include PostHog's default join keys `posthogDistinctId` and `sessionId`.
Error events also carry `$session_id`. Custom exception `module` is
exported as `exception_module` on logs to avoid Python's reserved key.
The agent emits one `agent_turn_finished` summary containing queryable
timing aggregates, an explicit outcome and the full `timings_json` list.
Session context reaches tools; request IDs stay in the transport layer.

Reporting boundaries attempt capture once and keep telemetry failures
from replacing the original error. Failures before telemetry startup
or after its shutdown remain local. Testing suppresses remote capture
and remote log export while retaining local records.

### Browser replay context

HTTP requests may send `X-POSTHOG-SESSION-ID`.
`PostHogSessionIdMiddleware` stores the trimmed value on
`request.state.posthog_session_id`; routes and exception handlers can
read it using `api.utils.requests.get_posthog_session_id(request)`.
Missing or blank values return `None`; no session ID is generated.

WebSocket clients may include `session_id` in the `/agent/ws/agent-chat`
handshake query string. The trimmed value is retained on
`ws.state.posthog_session_id` and `WebSocketManager.posthog_session_id`
for that connection. Reconnect with the current ID if the browser's
replay session changes. Existing clients may omit it.

When frontend tracking is implemented, configure PostHog
`tracing_headers` with the backend hostname, without protocol, port or
path. This supplies the HTTP header for fetch/XHR; the WebSocket query
parameter must be supplied explicitly. Backend user IDs continue to
come from application identity resolution, never the session ID or
`X-POSTHOG-DISTINCT-ID` header. This scaffolding does not start replay
recording or attach session IDs to telemetry yet.

### Environment configuration

Set `PORTFOLIO_AGENT_ENV` to `testing`, `development` or
`production`. The corresponding file must exist in the root:

| Environment   | Required file      |
|---------------| -------------------|
| `testing`     | `.env.testing`     |
| `development` | `.env.development` |
| `production`  | `.env.production`  |

Each file must configure:

- `PORTFOLIO_AGENT_ENV`: the matching environment name.
- `PORTFOLIO_AGENT_PORT`: the server port.
- `MONGODB_URI`: that environment's MongoDB connection URI.
- `OPENAI_KEY`: the OpenAI API key.
- `JWT_SECRET`: the token signing secret.
- `CORS_ORIGINS`: comma-separated permitted frontend origins.
- `COOKIE_DOMAIN`: the domain used for the access cookie.

Use separate MongoDB projects for testing, development and
production. Client limits and other optional settings have defaults
in their respective configuration modules.

## Run the server

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python run.py
```

`run.py` validates the environment and starts `api.server:app` on
`PORTFOLIO_AGENT_PORT`. Development enables automatic reload.
The application lifespan starts and stops MongoDB, OpenAI,
WebSocket, security and maintenance resources.

The current operating model is one application process and one
replica per database environment. See the
[single-instance operating model](docs/architecture/operating-model.md)
before changing worker or replica counts.

## Chat with the agent in the terminal

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python -m tests.agent.agent_input --verbosity 1
```

This interactive runner streams the actual agent's answers and
prints timings for the whole interaction, individual tool calls
and each OpenAI response round. It uses live MongoDB and OpenAI
clients. Bootstrap that environment's corpus before asking
portfolio questions.

Verbosity levels are `0` for minimal output, `1` for history and
tools, and `2` for SDK events. Timing summaries appear at every
level. Enter `exit` or `quit`, or press Ctrl-D, to finish.
The runner prints the visitor ID; reuse it to continue a stored
conversation:

```sh
uv run python -m tests.agent.agent_input --user-id <visitor-id>
```

## Run tests

Unit tests do not require service credentials:

```sh
uv run pytest -m unit
```

Live integration tests require `.env.testing` and use the testing
MongoDB project. Tests involving the agent or RAG also make real
OpenAI requests and require a bootstrapped testing corpus.

```sh
export PORTFOLIO_AGENT_ENV=testing
uv run python -m corpus.bootstrap
uv run pytest -m integration
```

Run the live agent WebSocket tests specifically:

```sh
uv run pytest tests/api/agent/integration
```

Run the complete suite with the testing environment selected:

```sh
uv run pytest
```

See the [test guide](tests/README.md) for package-specific commands,
fixtures, data cleanup and coverage.

## Bootstrap the corpus

```sh
export PORTFOLIO_AGENT_ENV=development
uv run python -m corpus.bootstrap
```

Run bootstrap separately for every database environment, with its
corresponding environment file present. It creates a missing
vector search index and uploads embedded corpus documents when
the collection is empty.

Existing indexes and records are retained. Bootstrap does not
refresh edited documents or reconcile partial uploads.
`corpus.push_corpus` appends records with fresh IDs, so it is not
an update command. See the [corpus guide](corpus/README.md) for the
individual upload and index commands.

## Project structure

| Path                                    | Responsibility                                                                  |
|-----------------------------------------| --------------------------------------------------------------------------------|
| `run.py`                                | Environment validation and Uvicorn startup.                                     |
| `api/`                                  | FastAPI routes, dependencies, middleware and service lifecycles.                |
| `api/websocket/`                        | Connection managers, registry, protocol helpers and delivery.                   |
| `agent/`                                | Conversation orchestration, prompts, streaming, tools, memory and visible chat. |
| `agent/observability/`                  | Reusable interaction, tool and model timing measurements.                       |
| `rag/`                                  | Input refinement, query planning, vector retrieval and context refinement.      |
| `corpus/`                               | Tagged portfolio documents, embeddings, uploads and index bootstrap.            |
| `schemas/`                              | Shared Pydantic models and enums for the API, agent, corpus and security.       |
| `users/`                                | Anonymous visitor CRUD operations.                                              |
| `authorisation/jwt/`                    | JWT creation, validation and token configuration.                               |
| `security/`                             | Rate limit store, usage and block records, observers and lifecycle.             |
| `database/mongodb/`                     | MongoDB client lifecycle and database/collection resolution.                    |
| `openai_client/`                        | OpenAI client lifecycle, model settings and request limits.                     |
| `shared/`                               | UTC time, ID generation, formatting and terminal logging helpers.               |
| `exceptions/`                           | Service-specific exceptions.                                                    |
| `tests/`                                | Scoped unit/integration suites, shared fixtures and the terminal runner.        |
| `docs/`                                 | API contracts, schemas, system features and architectural considerations.       |
| `terraform/aws/`, `terraform/mongodb/`  | Environment infrastructure definitions.                                         |
| `kubernetes/`, `Dockerfile`, `makefile` | Deployment assets requiring review against the v2 runtime.                      |

## Further documentation

- [API WebSocket model](docs/api/features/websockets.md)
- [Agent chat endpoint](docs/api/responses/agent/agent-chat.md)
- [Authentication model](docs/api/features/security.md)
- [RAG pipeline](rag/README.md)
- [MongoDB data model](docs/architecture/mongodb-data-model.md)
- [System features and retention](docs/system-features/README.md)
- [Schema reference](docs/schemas/README.md)

## Licence

Licensed under the [Apache License 2.0](LICENSE).
See [NOTICE](NOTICE) for attribution and additional details.
