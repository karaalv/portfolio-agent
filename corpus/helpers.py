"""Count tokens and load tagged corpus files for processing."""

import re
from pathlib import Path

import tiktoken

from openai_client.main import get_embedding
from schemas.corpus.file import CorpusFile
from schemas.corpus.item import CorpusItem
from shared.ids import generate_uuid_str


def get_token_count(
	text: str, encoding_name: str = 'o200k_base'
) -> int:
	"""Count plain-text tokens using the specified encoding.

	Use cl100k_base for text-embedding-3 inputs. This count
	excludes any message framing or tool-schema overhead.
	"""
	encoding = tiktoken.get_encoding(encoding_name)
	return len(encoding.encode(text, disallowed_special=()))


def get_corpus_files() -> list[CorpusFile]:
	"""List corpus Markdown files alphabetically without README.

	Resolve the documents directory from this module so discovery
	works independently of the current working directory.
	"""
	directory = Path(__file__).resolve().parent / 'documents'
	return [
		CorpusFile(
			file_path=path,
			label=path.stem.replace('_', ' ').title(),
		)
		for path in sorted(directory.glob('*.md'))
		if path.is_file() and path.name.casefold() != 'readme.md'
	]


async def load_corpus_from_file(
	file_path: str | Path, embeddings: bool = False
) -> list[CorpusItem]:
	"""Parse tagged sections, optionally embedding their context.

	Resolve relative paths against the working directory. Remove
	HTML comments and standalone separators, then normalise field
	whitespace. Preserve source labels and generate a fresh UUID
	for each item. Without embeddings, return empty vectors and
	make no API calls.
	"""
	path = Path(file_path)
	content = path.read_text(encoding='utf-8')
	content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
	content = re.sub(
		r'^[\t ]*---[\t ]*$',
		'',
		content,
		flags=re.M,
	)
	sections = re.findall(
		r'<section>(.*?)</section>', content, flags=re.DOTALL
	)
	items: list[CorpusItem] = []
	for section_number, section in enumerate(sections, start=1):
		fields = {
			tag: _extract_field(
				section,
				tag,
				path,
				section_number,
			)
			for tag in ('label', 'header', 'context', 'document')
		}
		items.append(
			CorpusItem(
				item_id=generate_uuid_str(),
				label=fields['label'],
				header=fields['header'],
				context=fields['context'],
				document=fields['document'],
				embedding=[],
			)
		)

	if embeddings:
		for item in items:
			item.embedding = await get_embedding(item.context)
	return items


def _extract_field(
	section: str, tag: str, path: Path, section_number: int
) -> str:
	"""Extract a required field or report a malformed section."""
	matches = re.findall(
		rf'<{tag}>(.*?)</{tag}>', section, flags=re.DOTALL
	)
	if len(matches) != 1 or not matches[0].strip():
		raise ValueError(
			f'{path}: section {section_number} must contain '
			f'exactly one non-empty <{tag}> field.'
		)
	return re.sub(r'\s+', ' ', matches[0]).strip()
