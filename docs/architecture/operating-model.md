# Single application instance

The current operating model assumes one application instance,
one serving process and one replica per database environment.
Concurrent requests within that instance are expected. Multiple
workers, replicas or overlapping deployments are outside the
current security and connection-management assumptions.

The app is configured around 50 concurrent chat users. This is
a capacity planning assumption, not a reason to add workers
without reviewing the responsibilities below.

## Responsibilities to revisit before scaling

- Observers: ownership of background jobs, shared database
  updates, reset boundaries and cleanup coordination.
- WebSocket management: connection ownership, stale connection
  cleanup and targeted disconnection across instances.
- WebSocket data streaming: routing events to the instance that
  owns a socket and preserving stream order and identity.
- Client instances and connections: ownership, lifecycle,
  per-process quotas and isolation of application instances.

The WebSocket manager will clear all persisted connection IDs
when created, before accepting sockets. This assumes no other
manager is serving connections in the same environment.

Monitoring creation helpers use local locks and have no unique
compound indexes. This does not guarantee uniqueness across
multiple processes. Reconsider database constraints on
`(entity, entity_id)` and concurrent creation if the operating
model changes.

Rate limit stores also remain local to each instance. Their
allowances would multiply across workers unless enforcement
were coordinated externally.

Separate test and deployed environments must use separate
database projects. Two apps using the same environment can
interfere even if they are started for different purposes.
