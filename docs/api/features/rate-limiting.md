# Rate limiting

## Structure

`schemas/security/ratelimit.py` defines caller types, resource
scopes, configuration and stored limiter metadata.
`security/ratelimit/config.py` maps scope and caller type to a
`RateLimitConfig`. Each `RateLimitStore` owns its limiter objects
and lock, rather than sharing module-level state.

The server lifecycle will create one store per app instance
inside its running event loop and await `stop()` at shutdown.
API dependencies and WebSocket message handling will use that
store when enforcement is connected.

## Callers and scopes

- `ResourceAccessor.IP`: the caller's trusted client IP address.
- `ResourceAccessor.USER`: the user ID from a verified JWT.
- `ResourceScope.SYSTEM`: `/health` requests.
- `ResourceScope.AGENT_MESSAGE`: each `ws.send_message` action.
- `ResourceScope.APPLICATION`: other API endpoints.

Authenticated operations should enforce both IP and user limits.
Unauthenticated operations can only enforce an IP limit. The
first anonymous message must be limited by IP before creating
its user. Raw tokens and client-supplied user IDs must not act as
authenticated identities. Only trust forwarded IP headers from
configured, trusted proxies.

## Initial allowances

All replenishment periods are 60 seconds. Allowances apply to
each identity within each scope, within each store.

| Scope | IP capacity | User capacity |
| --- | ---: | ---: |
| `SYSTEM` | 500 | 100 |
| `AGENT_MESSAGE` | 1,000 | 20 |
| `APPLICATION` | 3,000 | 60 |

Agent and application IP capacities accommodate 50 users sharing
an IP, each using their full individual allowance. Health checks
have a separate allowance; the user limit only applies if a user
is authenticated for that operation.

These are leaky-bucket capacities, not strict counts in fixed
minute windows. An idle limiter permits an initial burst up to
its capacity, then replenishes continuously over its period.
High IP capacities are intentionally permissive for shared
networks; anonymous traffic still requires further protection
when abuse monitoring is implemented.

## Store operations

`get_limiter` atomically returns or creates an `AsyncLimiter` for
the scope, caller type and identity. Retrieving a limiter does
not consume capacity. The lock protects store access, not the
execution of the caller's request.

Each stored `RateLimiter` has a unique `limiter_id` and a
timezone-aware UTC `last_accessed_at`, updated on every
`get_limiter` call. `get_all_limiters` returns a
shallow dictionary copy; its limiter objects remain shared.
`delete_limiter` and `delete_limiters_by_keys` remove entries and
ignore missing keys. Keys are distinct from `limiter_id` values.

Awaiting `acquire()` waits for capacity. API enforcement must
bound that wait or reject excess operations explicitly, rather
than allowing an unbounded request queue. HTTP rejection should
use status 429; WebSocket rejection needs a suitable error event.

## Lifetime and cleanup

A store and its limiters belong to one event loop. Different app
instances must receive different stores. Different workers have
independent allowances, and restarting a worker resets them.

Deletion resets the allowance for future lookups. Existing
references to a deleted limiter continue to exist. Cleanup must
avoid deleting active entries, which could create simultaneous
old and new limiters for the same identity.

Construction starts a background cleanup task. Every twelve
hours it removes entries last fetched more than three days ago.
`prune_once` checks inactivity and removes entries under the same
lock used for lookups, so a concurrent lookup cannot refresh an
entry between the inactivity check and deletion.

Access is tracked when fetching a limiter from the store, not
when acquiring capacity through an existing reference. Request
handlers must fetch the limiter for each operation, including
each WebSocket message, rather than cache it for a connection.

Cleanup starts after the first twelve-hour interval. Depending
on timing, an inactive entry can remain for up to another twelve
hours after crossing the three-day threshold. Failed cleanup
attempts are logged and retried at the next interval. `stop()`
cancels and awaits the task; it does not clear stored allowances.

Inactivity cleanup does not impose a hard bound on identities
added within the retention period. Monitoring must account for
large volumes of distinct callers.

## Implementation boundary

This package provides limiter storage and configuration.
Lifecycle integration, API enforcement and suspicious-activity
monitoring are subsequent steps.
