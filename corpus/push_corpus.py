"""
This module is used to push the corpus
data to the MongoDB collection.
"""

import asyncio
import os
import re

from common.utils import TerminalColors
from corpus.schemas import CorpusItem
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)
from database.mongodb.main import get_collection

# --- File Processing ---


async def _load_file(file_name: str) -> list[dict]:
	"""
	Load a file and return a list of CorpusItems.

	Args:
		file_name (str): The name of the file to load.

	Returns:
		list[CorpusItem]: The loaded corpus items.
	"""
	# Import embedding function here to get around
	# import issues
	from openai_client.main import get_embedding

	current_dir = os.path.dirname(os.path.abspath(__file__))
	file_path = os.path.join(current_dir, file_name)

	with open(file_path, encoding='utf-8') as file:
		content = file.read()

	# Clean comments
	cleaned = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
	cleaned = re.sub(r'\n\s*\n', '\n', cleaned)

	# Clean trailing spaces
	cleaned = re.sub(r'\s*\n\s*', ' ', cleaned, flags=re.MULTILINE)

	# Clear separators
	cleaned = re.sub(r'---', ' ', cleaned, flags=re.DOTALL)

	# Extract Sections
	sections = re.findall(r'<section>(.*?)</section>', cleaned, re.DOTALL)

	# Load content within sections into CorpusItems
	corpus_items: list[CorpusItem] = []
	for section in sections:
		id: list[str] = re.findall(r'<id>(.*?)</id>', section, re.DOTALL)
		header: list[str] = re.findall(
			r'<header>(.*?)</header>', section, re.DOTALL
		)
		context: list[str] = re.findall(
			r'<context>(.*?)</context>', section, re.DOTALL
		)
		document: list[str] = re.findall(
			r'<document>(.*?)</document>',
			section,
			re.DOTALL,
		)

		# Create a CorpusItem from the extracted content
		context_str: str = context[0].strip()
		corpus_item = CorpusItem(
			id=id[0].strip(),
			header=header[0].strip(),
			context=context_str,
			document=document[0].strip(),
			embedding=await get_embedding(context_str),
		)
		corpus_items.append(corpus_item)

	return [c.model_dump() for c in corpus_items]


# --- Main ---


async def main():
	await connect_mongo()

	print(f'{TerminalColors.yellow}Starting Corpus Push{TerminalColors.reset}')

	collection = get_collection('corpus')

	files = [
		'documents/personal.md',
		'documents/education.md',
		'documents/skills.md',
		'documents/projects.md',
		'documents/experience.md',
		'documents/meta_reflection.md',
	]

	for file in files:
		print(
			f'{TerminalColors.blue}'
			f'Processing file: {file}'
			f'{TerminalColors.reset}'
		)
		corpus_items = await _load_file(file)
		await collection.insert_many(corpus_items)
		print(
			f'{TerminalColors.magenta}'
			f'Inserted {len(corpus_items)} items from {file}'
			f'{TerminalColors.reset}'
		)

	await close_mongo()

	print(f'{TerminalColors.yellow}Finished Corpus Push{TerminalColors.reset}')


if __name__ == '__main__':
	import os

	from dotenv import load_dotenv

	load_dotenv(override=True, dotenv_path=os.path.abspath('.env'))
	asyncio.run(main())
