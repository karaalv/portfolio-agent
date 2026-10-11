# WebSocket connection model

## Scope

The portfolio uses direct delivery through a process-local
connection manager and registry. There is no shared event bus.
The controller, agent integration and application lifespan
wiring will be implemented separately. These base classes do
not accept sockets, authenticate users or read client messages.

## Modules

- `schemas/api/ws/request.py`: client request validation.
- `schemas/api/ws/response.py`: typed server response variants.
- `api/websocket/helpers/responses.py`: response construction.
- `api/websocket/manager.py`: one connection's outbound delivery.
- `api/websocket/registry.py`: tracking and inactivity cleanup.
- `exceptions/websocket.py`: lifecycle failure context.

## Response helpers

The helper module provides `create_ws_heartbeat_response`,
`create_ws_agent_start_response`, `create_ws_agent_end_response`,
`create_ws_agent_response`,
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
