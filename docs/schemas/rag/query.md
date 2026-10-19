# RAG query plan

Defined in `schemas/rag/query.py`. `plan_rag` produces this
schema and `execute_rag` consumes it.

## Structure

```python
class QueryPlan(BaseModel):
	queries: list[str]
	agent_thinking_captions: list[str]
```

## Fields

- `queries`: Required list of self-contained semantic searches
  about Alvin Karanja. Each query should cover a distinct part
  of the visitor's request without assuming unverified facts.
  At most three queries are permitted, using `MAX_QUERIES` from
  `rag/config.py`. An empty list means no retrieval is required.

- `agent_thinking_captions`: Required ordered list of brief
  progress captions, one per query. Each describes the search
  topic in plain text, using at most eight words. These captions
  do not expose internal reasoning or assert unverified facts.
  Return an empty list when no retrieval is planned. The list
  has the same maximum length as `queries`.

Pydantic enforces the list type and maximum length. Relevance,
meaningful query text, semantic overlap, caption word counts
and correspondence to queries are guided by the
planner prompt rather than validated by this schema.

## Example

```json
{
  "queries": [
    "Alvin Karanja portfolio agent architecture",
    "Alvin Karanja backend engineering experience"
  ],
  "agent_thinking_captions": [
    "Exploring Alvin's portfolio agent architecture",
    "Checking Alvin's backend engineering experience"
  ]
}
```


## Delivery

After planning, `rag.main.fetch_context` sends an
`agent_thinking_captions` WebSocket response to the requesting
connection before calling `execute_rag`. Its payload is the
ordered caption list. Direct RAG callers without a connection
ID skip socket delivery. Captions are display metadata and are
not persisted as model memory or included in supporting context.
