# WebSocket connection model

## Scope

The portfolio uses direct delivery through a process-local
connection manager and registry. There is no shared event bus.
The chat route invokes the agent directly and streams output to
the requesting connection. The manager and registry do not
authenticate users or read client messages.

## Modules

- `schemas/api/ws/request.py`: client request validation.
- `schemas/api/ws/response.py`: typed server response variants.
- `api/websocket/helpers/responses.py`: response construction.
- `api/websocket/manager.py`: one connection's outbound delivery.
- `api/websocket/registry.py`: tracking and inactivity cleanup.
- `api/websocket/lifecycle.py`: process-local registry access.
- `exceptions/websocket.py`: lifecycle failure context.

## Agent chat endpoint

Connect to `/agent/ws/agent-chat`, beneath the API root, with an
optional `access_token` query parameter. IP access is checked
before acceptance. Supplied tokens are validated and subject to
user blocking and application rate limits. Invalid supplied
tokens are rejected rather than replaced with new identities.

The optional query `request_id` identifies the handshake.
Each client message can supply its own `request_id`; missing,
null or empty IDs receive generated UUID strings. Agent messages
update the manager's current request ID; heartbeats do not.
Response helpers create fallback metadata, then the manager
stamps a copied response at enqueue time with its current ID.
This preserves correlation while queued responses await sending.
See `docs/api/responses/agent/agent-chat.md` for the protocol.

Without a token, the route creates an anonymous user and user
usage record. After accepting and registering the socket, it
queues `set_user_token` immediately after registry registration.
This carries the token for the cookie claim flow and is sent once.

Requests are validated as `WebSocketRequest`. Heartbeats are
ignored and do not consume agent-message capacity. Each agent
message acquires both IP and user allowances before invoking
`agent_chat`. Turns run sequentially on the connection.

Malformed requests close with `1008`; rate-limit timeouts close
with `1013`. Disconnect handling removes and closes the tracked
connection.

### Input safety

The request helper checks the entire UTF-8 envelope against
16 KiB before parsing JSON. Heartbeat messages are included.
Agent payloads are checked against 10,000 model tokens before
sanitisation. Counts use the `o200k_base` encoding and treat
special token markers as ordinary text.

Exceeding either limit persists a 24-hour user block and closes
every local connection for that user with `1009`. It does not
block the IP. Block persistence failures still close connections,
but cannot guarantee future access will be denied.

`agent/input/sanitisation.py` provides `sanitise_input`.
It normalises Unicode and whitespace, removes control characters,
obvious repetition and uninterrupted strings over 100 characters,
then truncates cleaned text to 2,000 characters. It does not
redact personal data or classify text by English vowel ratios.
Empty cleaned input receives a warning and skips agent execution.

Limits are configured in `agent/config/input.py` and
`api/config/websocket.py`. The tokeniser caches its vocabulary;
its initial load may download the standard encoding file.
`run.py` configures Uvicorn's transport ceiling at 64 KiB per
incoming WebSocket message. The application still blocks at
16 KiB. Messages rejected at the transport ceiling never reach
the application byte guard, so it cannot persist their blocks.

### Agent stream delivery

The route passes its connection ID to `agent_chat`. Direct
terminal and integration callers can omit it and use the agent
without a running WebSocket registry.

Each turn queues `agent_start`, then `agent_delta` messages for
text chunks. A delta carries a `StreamManagerItem`; its payload
is incremental text, not the whole accumulated response.
`sequence_number` increases across recursive model rounds.

Tool rounds publish `tool_message` with the set of requested
tool names before dispatch. Recursion retains the same socket
and stream manager. Only one `agent_end` is queued for the turn,
after all tool rounds finish or a terminal failure is handled.
An output item's completion does not end the whole agent turn.

`response.failed` and explicit stream errors produce `error`.
`response.incomplete` produces `warning`. A stream that ends
without `response.completed` also produces `error`. These paths
stop the turn without executing pending tools or persisting that
round's incomplete output. Already streamed text can remain
visible but must not be treated as a completed saved response.

Only `response.completed` output is persisted for model replay.
The model stream is closed before tool execution and recursion.
`agent_end` means the turn stopped, not that it succeeded. The
preceding warning or error tells the client about failure.

## Registry lifecycle and package access

The API lifecycle starts the registry after service clients.
Shutdown closes its connections and stops cleanup before
closing the OpenAI and MongoDB clients.

Import lifecycle helpers directly from `api.websocket`:

```python
from api import websocket

registry = websocket.get_websocket_registry()
queued = await websocket.send_connection(
    user_id, connection_id, response
)
```

Startup and shutdown are idempotent. Access before startup
raises `WebSocketRegistryException`. The send helper returns
false for missing or closed connections; true means queued.
`set_websocket_registry` replaces the reference for tests; it
does not start or stop either instance. The caller owns those
lifecycles. Each process holds its own registry and connections.

## Response helpers

The helper module provides `create_ws_heartbeat_response`,
`create_ws_agent_start_response`, `create_ws_agent_end_response`,
`create_ws_agent_delta_response`,
`create_ws_tool_message_response`,
`create_ws_set_user_token_response`,
`create_ws_warning_response` and `create_ws_error_response`.

Each helper returns its concrete response variant and timestamps
shared API metadata with `get_utc_datetime_now()`.

## Connection manager

`WebSocketManager` owns one accepted socket, its user and
connection IDs, and optional current request ID. `created_at`
and `last_message_at` are timezone-aware UTC datetimes.

`start()` creates sender and heartbeat tasks once. A closed
manager cannot restart. All response messages go through one
FIFO queue and one sender task, `_send_queued_messages`.
Heartbeats do not bypass queued agent output.

The controller must call `record_message(request_id)` for an
incoming non-heartbeat application message. Successfully sent
non-heartbeat responses also update `last_message_at`.
Heartbeat sends and replies must not count as application
activity, otherwise an unused connection would never expire.

### Resource limits

| Setting | Value |
| --- | --- |
| Outbound queue size | 333 messages |
| Heartbeat interval | 30 seconds |
| Maximum wait for queue space | 5 seconds |
| Maximum wait for one socket send | 10 seconds |
| Maximum wait for socket closure | 5 seconds |

Queue size is a message-count limit, not a byte-size limit.
Incoming message and payload-size limits belong to the later
controller and server configuration.

`send_message()` returns true when output is queued. This is
not confirmation that the client received or applied it.
Closed managers return false. Unexpected enqueue errors are
logged and drop that item, returning false. Callers must handle
that result, especially for agent stream and token messages.

A queue-space timeout closes the socket with `1013`. A socket
send timeout also uses `1013`. Other sender or heartbeat
failures use `1011`. Cancellation remains cancellation and is
not reported as an application error.

`close()` is idempotent, stops and awaits owned background
tasks, discards pending output, unblocks waiting producers and
attempts a bounded socket close. A task initiating closure is
not cancelled or awaited by itself. Failures include operation,
connection, user and request identifiers in logging context.

Application heartbeat messages are JSON messages, not WebSocket
protocol ping frames. Sending them alone does not prove that a
client is reading or replying. Reply handling belongs to the
controller.

## Connection registry

The registry tracks:

```python
_registry: dict[str, dict[str, WebSocketManager]]
# user_id -> connection_id -> manager
```

`add_connection()` expects an accepted socket and starts its
manager. Duplicate user/connection keys are rejected rather
than replacing and leaking an existing manager.

Queries include `has_user`, `has_connection`, `get_connection`
and `count_connections`. Counts describe tracking state;
already closed managers may remain until removal or cleanup.

Removal methods detach tracking state and close the managers:

- `remove_connection`: one connection.
- `remove_user_connections`: all connections for one user.
- `remove_users_connections`: connections for selected users.
- `close_all_connections`: all currently tracked connections.

State changes occur under an `asyncio.Lock`. Socket sends and
closure occur outside it. Detached managers close concurrently,
and cancellation waits for their cleanup before propagating.

`send_connection()` is the only registry messaging operation.
It targets one user's connection and reports queue acceptance.
There is no user-wide broadcast operation.

### Inactivity cleanup and lifecycle

Call `start()` in a running event loop to start registry cleanup.
Every fifteen minutes it removes closed managers and connections
whose last application message was at least one hour ago.
Inactive sockets close with `1001`. Cleanup timing means an
idle connections can remain for fifteen extra minutes,
plus event-loop scheduling and cleanup delays.

Call `stop()` during shutdown. It rejects further registrations,
stops and awaits the cleanup task, and closes tracked sockets
with `1001`. A stopped registry cannot restart.

The future controller must remove its connection in `finally`
on disconnect rather than relying on periodic cleanup alone.

## Operating boundary

Managers, tasks, locks and the registry belong to one process
and event loop. Another worker cannot access these sockets.
The current operating model remains one serving process.

Security counters, persisted connection bookkeeping, agent
cancellation and authentication are not managed by these base
classes. Those responsibilities belong to later integration.
