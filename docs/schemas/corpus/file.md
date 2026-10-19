# Corpus file schema

`CorpusFile` identifies a source file in the corpus processing
pipeline. It describes the file without loading its contents or
generating embeddings.

Defined in `schemas/corpus/file.py`.

## Structure

```python
class CorpusFile(BaseModel):
	file_path: Path
	label: str
```

Both fields are required.

## Fields

- `file_path`: A filesystem path represented by `pathlib.Path`.
- `label`: A human-readable label used during corpus processing.

## File discovery

`get_corpus_files()` in `corpus/helpers.py` returns these objects
for Markdown files directly within `corpus/documents`.

- Files are returned alphabetically by filename.
- `README.md` is excluded because it documents the directory.
- Paths are absolute and independent of the working directory.
- Labels come from filename stems, with underscores replaced by
  spaces and title case applied. For example,
  `meta_reflection.md` becomes `Meta Reflection`.
