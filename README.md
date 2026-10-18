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

### Analytics and observability

The canonical [agent PostHog integration guide](https://github.com/karaalv/portfolio-documentation/blob/main/analytics/agent.md) lives in
`portfolio-documentation/analytics/agent.md`. It documents identity,
exception ownership, log events, span boundaries, AI attribution and
frontend responsibilities. Update that guide when changing the contract.

The agent sends explicit exception events, structured application logs,
OTLP spans and wrapped OpenAI telemetry in development/production.
Those environments require `POSTHOG_API_KEY` (the project token) and
`POSTHOG_HOST`. Testing retains local logs and uses disabled AI capture;
it does not require PostHog credentials or send telemetry.

Use `shared.logging.log_*` for structured logs and
`posthog_client.tracing.start_span` around application operations.
Failure boundaries use `posthog_client.error_tracking.report_exception`.
`AIContext` is set once per agent turn; OpenAI helpers read it with
`generation_options_from_context()`. Prompt and response capture is on.

The API, corpus entry points and terminal runner start PostHog before the
wrapped OpenAI client in active environments and drain telemetry last.
HTTP replay context arrives through `X-POSTHOG-SESSION-ID`; WebSockets
use the handshake `session_id` query parameter. The backend remains the
authority for visitor identity. Browser replay recording and frontend
identification still need frontend implementation.

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

Development and production also require `POSTHOG_API_KEY` and
`POSTHOG_HOST`; testing does not. The API key is the PostHog project
token, not a personal API key.

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

## Build and deploy

Set your AWS profile and Kubernetes context before using the
Makefile. It uses the AWS CLI, regular Docker, kubectl and
`envsubst`. The default region is London (`eu-west-2`).
`SERVICE_NAME` is defined in the Makefile, and the ECR repository
name defaults to that value: `portfolio-agent`.

### Deployment environment

`PORTFOLIO_AGENT_ENV=production` selects production. Every other
value, including an unset variable, selects staging.

| Setting | Staging, default | Production |
| --- | --- | --- |
| Secrets Manager ID | `portfolio-agent/env/staging` | `portfolio-agent/env/production` |
| Kubernetes environment secret | `portfolio-agent-env-staging` | `portfolio-agent-env-production` |
| Deployment and Service name | `portfolio-agent-staging` | `portfolio-agent-production` |
| NodePort | `30002` | `30001` |

Both use namespace `default` and registry secret
`regcred-portfolio-agent`. These defaults can be overridden with
Make variables. Distinct names, selectors and NodePorts allow
both deployments to coexist while keeping one replica per
environment. `Recreate` prevents overlapping replicas during
updates and means a deployment has downtime while it restarts.

This is deployment selection. The application's actual runtime
`PORTFOLIO_AGENT_ENV` comes from the selected environment secret;
it must use a value accepted by the application environment
loader (`testing`, `development` or `production`). The Makefile
does not inject its default `staging` value into the container.

### Targets

| Target | Operation |
| --- | --- |
| `registry-login` | Authenticate Docker with ECR. |
| `build` | Build the commit-tagged image and tag it as `latest`. |
| `push` | Authenticate, then push both existing local image tags. |
| `build-push` | Build, authenticate and push both tags. |
| `reg-credentials-secret` | Refresh Kubernetes ECR pull credentials. |
| `env-secret` | Refresh the selected environment's settings secret. |
| `secrets` | Refresh both registry and environment secrets. |
| `validate-manifest` | Check that the combined Deployment/Service manifest exists. |
| `image-ref-available` | Check that the selected image tag exists in ECR. |
| `deploy` | Check the image, refresh secrets, apply resources and wait for readiness. |
| `rollout` | Refresh secrets, restart the deployment and wait for readiness. |
| `rollout-status` | Inspect and wait for the selected deployment's rollout. |
| `terminate` | Delete the selected Deployment and Service, stopping its pods. Secrets are retained. |

`deploy` and `rollout` explicitly depend on `secrets`. The
Makefile runs prerequisites serially, including with `make -j`,
so image checks and secret refreshes complete before deployment
operations. Updating secrets alone does not restart existing
pods; use `rollout` to load changed environment values.

```sh
make build-push
make deploy
make rollout
make rollout-status
make terminate
```

Those commands select staging unless production is explicitly
selected in the calling environment or on the command line:

```sh
PORTFOLIO_AGENT_ENV=production make deploy
PORTFOLIO_AGENT_ENV=production make rollout
PORTFOLIO_AGENT_ENV=production make terminate
```

`IMAGE_REF` is the canonical image reference passed to the single
Deployment/Service manifest. Its default combines the resolved
AWS account, London ECR registry, service repository and
`IMAGE_TAG` (the current Git commit). Deployments use
`IfNotPresent`; use a new commit tag for new image contents.
`rollout` restarts the deployed image rather than selecting a
new tag. Both health probes use `/api/system/health`.

Regular `docker build` targets `linux/arm64`, matching the
Graviton host. Non-ARM builders need ARM emulation; the GitHub
workflow configures QEMU. `BUILD_PLATFORM` can be overridden.

```sh
make deploy IMAGE_TAG=<published-tag> ROLLOUT_TIMEOUT=300s
make -n deploy
```

Dry runs print recipes without contacting AWS or Kubernetes.
Temporary environment files are private and removed on exit,
including on failure. Terraform now declares repository
`portfolio-agent`; review its plan and provide the new repository
and environment secret IDs before deploying. Existing resources
named `portfolio-agent` and `portfolio-env-prod` are legacy names
and are not renamed automatically by these commands. The older
EC2 bootstrap scripts also require review against this flow.

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
| `openai_client/`                        | Wrapped OpenAI client lifecycle, model settings and request limits.             |
| `posthog_client/`                       | Event client, OTLP pipelines, exception reporting and AI context.               |
| `shared/`                               | UTC time, ID generation, formatting and structured/terminal logging helpers.               |
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
