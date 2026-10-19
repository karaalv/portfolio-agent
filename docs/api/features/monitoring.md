# Usage monitoring and blocking

## Design status

Usage CRUD, block CRUD, allowance enforcement and observer
classes are implemented. API lifecycle and WebSocket integration
remain separate steps.

## Structure and persistence

MongoDB is the source of truth. The `analytics` database contains
the `usage` and `blocked` collections. Usage and block operations
write directly to MongoDB, without in-memory write-back queues.

Schemas belong in `schemas/security/monitoring/usage.py` and
`schemas/security/monitoring/blocked.py`. CRUD modules belong in
`security/monitoring/usage` and `security/monitoring/blocked`.
The legacy root `monitoring` package has been removed.

Background maintenance belongs in `security/observers`, with
separate usage and block observers.

## Usage records

`UsageEntity` identifies either `IP` or `USER`. Each
`UsageStatistics` record contains:

- `entity`: the entity type.
- `entity_id`: the trusted IP or authenticated user ID.
- `usage_day`: the UTC counter date as a `YYYY-MM-DD` string.
- `daily_requests`: counted application requests and incoming
  chat messages, excluding health checks and streamed output
  events.
- `daily_input_tokens`: tokens in incoming user messages.
- `active_ws_connections`: registered connection IDs.
- `last_request_at`: the latest counted request or message,
  represented as a timezone-aware UTC datetime.

Input tokens measure incoming message usage. They do not include
replayed history, instructions or tool results. Model cost
accounting is outside this feature's scope.

## Daily resets

On each counted request, check the record's `usage_day`. If it is
older than today's UTC date, reset its daily counters and advance
the day before recording the new operation.

The usage observer wakes at UTC midnight and resets records whose
day is older than today. It then sleeps until the next midnight.
This reconciles records that receive no new requests. It also
reconciles once when started to catch up after downtime.

Resets must update the counters and day together, with a
condition that prevents overwriting a record already advanced to
the current day by another operation. Active connections and
`last_request_at` are not reset by daily maintenance.

Blocked entities can have their daily counters reset. Their block
record continues to determine access independently.

## Policies and thresholds

`UsageScope` defines `DAILY_REQUESTS`, `DAILY_TOKENS` and
`ACTIVE_WS`. Each `UsagePolicy` defines a scope and limit. The
policy mapping belongs in `security/monitoring/usage/config`.

IP and user policies are separate. Aggregate IP allowances must
support 50 concurrent users sharing one address. Individual
allowances should be high enough for reasonable portfolio use.

The user connection limit is four. Attempting to register a fifth
connection triggers a block. IP connection allowances must
accommodate the aggregate usage rather than reuse this individual
threshold.

Initial allowances are:

| Scope | User limit | IP limit |
| --- | ---: | ---: |
| Daily requests | 1,000 | 50,000 |
| Daily input tokens | 500,000 | 25,000,000 |
| Active connections | 4 | 200 |

The operation that exceeds a limit triggers blocking. Counters
include that operation. Connection registration uses unique IDs
so registering the same connection twice does not consume two
slots. Rejected connections must be removed by the manager's
cleanup path.

## Block records

`BlockedEntity` identifies either `IP` or `USER`. Each
`BlockedRecord` contains `entity`, `entity_id`, `blocked_at`,
`blocked_until` and `reason`. Timestamps are timezone-aware UTC
datetimes.

When an allowance is exceeded, `apply_24h_block` creates a block
only if one does not already exist. It preserves an existing
block's reason and timestamps, rather than extending it after
each rejected attempt. A new record sets `blocked_until` to 24
hours after `blocked_at`.

The block must be persisted before raising the exception that the
API will translate into an access-denied response.

If a block record exists, the entity is blocked, even after
`blocked_until`. The block observer runs every six hours and
deletes records whose expiry has elapsed. Deletion restores
access. Daily usage resets do not delete blocks. The observer
also prunes once at startup.

With a healthy observer, blocking generally lasts 24 to 30 hours.
Delayed maintenance or downtime can extend that period. Visitors
receive a blocked notification without an unblock time.

## Concurrent writes and identity

No unique compound index is created in the current model. User
usage records will be created alongside user creation in the
WebSocket controller, before other operations update them. IP
records must likewise be explicitly created before updates. The
creation helper returns an existing record if present.

Creation helpers use process-local locks around checking and
inserting. This supports the single application instance model;
it does not coordinate different processes or external writers.
Usage updates must use atomic database operations rather than
overwrite counters from an earlier read.

Request recording resets an older day and increments its counters
in one atomic update pipeline. Reconciliation only resets older
days, preserving usage already recorded for today.

Duplicate block records are tolerated, not actively merged.
Access checks consider any matching record; manual deletion
removes all matches and expiry pruning deletes eligible records.
Different expiry timestamps could keep access blocked until the
last duplicate is removed. This is acceptable for this model.

For future versions, reconsider a unique compound index on
`(entity, entity_id)` in each collection. It would enforce one
record per identity across concurrent writers. A compound index
only enforces uniqueness when configured with `unique=True`.

## Usage retention

The usage observer also prunes records after ten days of
inactivity, using `last_request_at`. This is separate from the
seven-day application user-data retention policy.

Usage pruning currently deletes eligible database records at
startup and during daily maintenance. Closing associated user
connections will be connected during WebSocket management work.

## Connection startup model

For one serving process and one replica, the connection manager
will clear all `active_ws_connections` lists when created, before
accepting connections. This removes stale registrations left by a
process crash. Daily counters and blocks are retained.

Normal disconnect and exception cleanup remove individual
connection IDs. Daily resets do not clear live registrations.

This strategy requires exclusive ownership of the deployment's
connection state. It is unsafe with multiple workers, replicas or
overlapping deployments because startup could erase another
process's live registrations. A shared testing environment can
also interfere if two apps operate on the same records.

Before changing that operating model, replace the global reset
with connection ownership and expiry handling. Implementation of
connection management remains a separate step.

## API integration contract

Request handling must check existing IP and user blocks before
performing an operation. The helper `enforce_existing_block`
raises for any matching block record, including one awaiting
expiry cleanup. `apply_24h_block` persists or reuses a block and
raises `EntityBlockedException` carrying that record.

Usage updates require an existing record; they do not silently
create one. Updates return the new `UsageStatistics` and enforce
its allowances. Removing a connection does not enforce limits, so
cleanup remains possible while the entity is blocked.

Observers provide `start`, `stop` and `run_once`. Start them
after MongoDB connects and stop them before closing MongoDB. No
server lifecycle or request wiring is added at this stage.

See the [single-instance
model](../../architecture/operating-model.md) before changing
process or deployment ownership.
