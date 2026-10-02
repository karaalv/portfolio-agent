# Corpus item schema

`CorpusItem` represents one portfolio knowledge-base entry.
It stores the content used to ground agent answers, a retrieval
progress label, and the vector used for similarity search.

Defined in `schemas/corpus/item.py`. Records are stored in
`application.corpus`.

## Structure

```python
class CorpusItem(BaseModel):
	item_id: str
	label: str
	header: str
	embedding: list[float]
	context: str
	document: str
```

All fields are required.

## Fields

- `item_id`: A UUID version 4 string generated with the shared
  `generate_uuid_str` helper when loading the entry. Each load
  creates a fresh identifier, so reloading does not deduplicate
  existing records by `item_id`.
- `label`: The source section's `<label>` value, for example,
  `projects_portfolio_agent`. This is preserved when loading
  the document and is separate from the generated identifier.
- `header`: A label displayed in the interface while context is
  retrieved. Use the format `Retrieving <topic>`, for example,
  `Retrieving Alvin's project experience`. This describes
  retrieval progress rather than the model's internal reasoning.
- `embedding`: The vector generated from `context`, used for
  similarity search. The full `document` is not the embedding
  input.
- `context`: A concise description of the entry's information.
  It provides the search representation and a quick overview of
  the content.
- `document`: The full content supporting the entry. It supplies
  the detailed information used to ground the agent's answer.
