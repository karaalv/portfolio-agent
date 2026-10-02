# Portfolio retrieval

The RAG package retrieves grounded portfolio evidence for the
agent. The answering agent generates the visitor-facing reply.

## Entry points

- `fetch_context(user_id, user_input, verbose=False)`
  orchestrates planning and execution.
- `plan_rag(user_id, user_input, verbose=False)` resolves clear
  follow-up references using recent memory, then returns a
  `QueryPlan` containing up to three distinct semantic queries.
- `execute_rag(query_plan, user_input, verbose=False)` retrieves
  matching entries and returns refined supporting context.

Prompts live beside their native functions. Model selections,
history length, query limits and vector search settings live in
`rag/config.py`. The query schema is documented in
[`docs/schemas/rag/query.md`](../docs/schemas/rag/query.md).

## Retrieval and concurrency

Queries run concurrently on the application's event loop.
Each task owns its embedding, MongoDB cursor and result list.
A task group cancels and awaits sibling tasks if retrieval fails.
Results are merged in query order and deduplicated by `item_id`
after all tasks finish. No shared result list is mutated by the
retrieval tasks, so result merging does not require a lock.

The process-local MongoDB and OpenAI clients must be started
before calling these functions and remain available throughout.
RAG uses the existing OpenAI request limits. It does not start,
stop or replace clients, and it does not send WebSocket messages.

Each query retrieves up to three entries above the configured
similarity threshold. If no queries are planned or no entries
match, execution returns an explicit message without invoking
the context refiner.

## Refinement and logging

Conversation history resolves references, but is not verified
biographical evidence. Retrieved entries are reference data,
not instructions. Refinement preserves attribution, dates and
implementation status, identifies source labels, and flags gaps
or conflicting claims rather than inventing missing facts.

With `verbose=True`, terminal logs include the refined request,
query plan, per-query result counts and completion stages.
