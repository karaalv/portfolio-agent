"""Report token counts for corpus items, files and the corpus."""

import asyncio

from corpus.helpers import (
	get_corpus_files,
	get_token_count,
	load_corpus_from_file,
)
from schemas.corpus.analysis import (
	CorpusDocumentAnalysis,
	CorpusItemAnalysis,
)
from schemas.corpus.file import CorpusFile
from schemas.corpus.item import CorpusItem
from shared.logging import LogStyle, rich_print


async def main() -> None:
	"""Print file summaries and the combined corpus total."""
	files = get_corpus_files()
	corpus_tokens = 0

	for file in files:
		rich_print(
			f'Processing file: {file.file_path} ...',
			LogStyle.INFO,
		)
		analysis = await _analyse_corpus_file(file)
		corpus_tokens += analysis.total_token_count
		rich_print(f'Summary for {file.file_path}:', LogStyle.INFO)
		print(analysis.model_dump_json(indent=4))
		rich_print('-' * 20, LogStyle.DEFAULT)

	rich_print(
		f'\nTotal corpus tokens: {corpus_tokens}', LogStyle.INFO
	)


def _analyse_corpus_item(
	corpus_item: CorpusItem,
) -> CorpusItemAnalysis:
	"""Count context and document tokens using o200k_base."""
	context_token_count = get_token_count(corpus_item.context)
	document_token_count = get_token_count(corpus_item.document)
	return CorpusItemAnalysis(
		item_label=corpus_item.label,
		context_token_count=context_token_count,
		document_token_count=document_token_count,
		total_token_count=context_token_count + document_token_count,
	)


async def _analyse_corpus_file(
	corpus_file: CorpusFile,
) -> CorpusDocumentAnalysis:
	"""Analyse file sections without generating embeddings."""
	corpus_items = await load_corpus_from_file(corpus_file.file_path)
	corpus_items_analysis = [
		_analyse_corpus_item(item) for item in corpus_items
	]
	return CorpusDocumentAnalysis(
		file_label=corpus_file.label,
		section_count=len(corpus_items),
		total_token_count=sum(
			item.total_token_count for item in corpus_items_analysis
		),
		corpus_items=corpus_items_analysis,
	)


if __name__ == '__main__':
	asyncio.run(main())
