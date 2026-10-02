# RAG query plan

Defined in `schemas/rag/query.py`. `plan_rag` produces this
schema and `execute_rag` consumes it.

## Structure

```python
class QueryPlan(BaseModel):
    queries: list[str]
```

## Fields

- `queries`: Required list of self-contained semantic searches
  about Alvin Karanja. Each query should cover a distinct part
  of the visitor's request without assuming unverified facts.
  At most three queries are permitted, using `MAX_QUERIES` from
  `rag/config.py`. An empty list means no retrieval is required.

Pydantic enforces the list type and maximum length. Relevance,
meaningful query text and semantic overlap are guided by the
planner prompt rather than validated by this schema.

## Example

```json
{
  "queries": [
    "Alvin Karanja portfolio agent architecture",
    "Alvin Karanja backend engineering experience"
  ]
}
```
