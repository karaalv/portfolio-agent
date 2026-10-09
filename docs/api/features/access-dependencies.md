# HTTP access dependencies

## Dependency chain

`api/dependencies/auth` exports three composable dependencies:

1. `require_ip_access` resolves the server-provided client host,
   acquires the IP's `APPLICATION` allowance and checks for an
   IP block.
2. `require_access_token` depends on the IP gate and validates
   the access-token cookie, returning its verified user ID.
3. `require_application_access` depends on token validation,
   checks for a user block and acquires that user's
   `APPLICATION` allowance.

Protected application routes should use `ApplicationUserId`, an
`Annotated` alias for the complete chain. `AccessUserId` provides
token validation after the IP gate, without user block or user
rate-limit enforcement. `IPAccess` provides the IP gate alone.

FastAPI resolves these dependencies before the route runs. A
shared dependency is cached within the request, so requesting
`IPAccess` alongside `ApplicationUserId` does not charge IP
capacity twice. No `Depends` function defaults or B008
suppressions are required.

The cookie name is configured as `JWT` in
`api/config/cookies.py`, matching the existing cookie name.
Usage counters are not updated by these dependencies; counted
operations will be connected separately.

## Errors and execution order

- Missing client address: HTTP 400.
- Missing, expired or invalid access token: HTTP 401.
- Existing IP or user block: HTTP 403 with a generic message.
- Exhausted limiter wait: HTTP 429.
- Token configuration, database or limiter service failure:
  HTTP 500 with a generic message.

The IP allowance is acquired before token validation and block
lookups, including attempts with invalid credentials. User
checks happen only after authentication. A blocked user is
rejected before acquiring their user allowance. IP capacity
already consumed by an attempt is not refunded if a later
check rejects it.

Token validation errors are distinct from application failures.
Internal exception causes are preserved for diagnostics without
exposing signing configuration or blocking reasons in responses.

## Acquisition timeouts

`api/utils/ratelimit.py` provides ordinary async acquisition
helpers. They do not hold or release concurrency slots.

`api/config/timeouts.py` sets the maximum wait for capacity:

- HTTP: 0.1 seconds.
- WebSocket handshake: 0.05 seconds.

These do not limit the duration of a request or handshake after
capacity is acquired. Only `limiter.acquire()` is timed.
Cancellation propagates during shutdown.

The HTTP helper raises 429 on timeout. The WebSocket helper
raises `WebSocketException` with code 1013 and leaves transport
handling to the controller. Before a socket is accepted, denial
normally appears as an HTTP handshake rejection rather than a
WebSocket close frame.

## Security client lifecycle

`security/lifecycle.py` owns one process-local `RateLimitStore`.
The API lifespan uses `api/security/security_manager.py` to
start this client after the MongoDB and OpenAI clients, then
start the usage and block observers. Repeated startup is
idempotent.

Shutdown stops maintenance, then both security observers and
the security client, before closing the API clients. The
manager cleans up partial security startup and attempts all
security shutdown steps even if an earlier step fails.

`get_security_client` requires prior startup. `get_limiter`
forwards to that store, allowing dependency code to retrieve an
allowance without managing its lifetime.

`stop_security_client` cancels and awaits the store's background
cleanup before clearing the reference. Repeated shutdown is
safe. `set_security_client` supports explicit injection, without
stopping a displaced store; its caller owns that cleanup.

This follows the single-instance operating model. Separate app
instances within one process must not replace each other's
store. Existing references are not migrated when the client is
replaced.

## Integration boundary

The security services are connected to the server lifespan.
Production routes and cookie claiming still need migration.
The legacy authentication module remains until route migration.

WebSocket dependencies and per-message enforcement will be
connected with the controller. HTTP dependencies do not enforce
limits on individual messages of an accepted socket.
