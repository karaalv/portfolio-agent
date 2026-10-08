# Scaling considerations

## Current assumption

The application is generally configured for 50 concurrent users
actively engaging with the chat. This is the current planning
assumption; adjust it using observed traffic, latency and costs.
It is not a verified throughput or latency guarantee.

Per-user rate limits control an individual's request frequency.
IP limits for chat messages and general application operations
allow 50 users sharing one address to use their individual
allowances. They do not reserve 50 simultaneous execution slots
or impose a global concurrency cap.

Actual capacity also depends on model and embedding quotas,
client concurrency limits, database performance, stream duration,
server resources and the number of tool calls per turn. Load
testing is required to establish the supported chat workload.

## Multiple workers

Each worker is a separate process with its own clients and rate
limit store. Worker-local limits are compatible with this model,
but a caller reaching several workers can consume an allowance
in each. Restarts also reset the worker's limiter state.

If application-wide enforcement becomes necessary, use a shared
limiter backend or an upstream control that coordinates across
workers and replicas. Revisit these assumptions before treating
worker-local limits as a global abuse or cost boundary.
