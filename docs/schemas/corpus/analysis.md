# Corpus analysis schemas

Defined in `schemas/corpus/analysis.py` and produced by
`corpus/analysis.py`. All fields are required.

## Item analysis

```python
class CorpusItemAnalysis(BaseModel):
	item_label: str
	context_token_count: int
	document_token_count: int
	total_token_count: int
```

- `item_label`: The source label from `CorpusItem.label`.
- `context_token_count`: The number of tokens in `context`.
- `document_token_count`: The number of tokens in `document`.
- `total_token_count`: The sum of both counts.

## Document analysis

```python
class CorpusDocumentAnalysis(BaseModel):
	file_label: str
	section_count: int
	total_token_count: int
	corpus_items: list[CorpusItemAnalysis]
```

- `file_label`: The display label from `CorpusFile.label`.
- `section_count`: The number of parsed sections in the file.
- `total_token_count`: The sum of all item totals in the file.
- `corpus_items`: Item summaries in source section order.

## Counting behaviour

Both text fields use the helper's default `o200k_base` encoding.
These are plain-text counts, excluding headers, labels, message
framing and tool-schema overhead. They are not embedding-model
counts or the token usage of a complete agent request.

Analysis loads documents without generating embeddings and makes
no OpenAI requests. Running it prints each document summary as
JSON, followed by the combined corpus token count:

```sh
uv run python -m corpus.analysis
```

Run the command from the repository root. The first token count
may download tiktoken's encoding data if it is not cached.
