"""
This module contains the main processing
logic for corpus data. This file is mainly
used to transform and analyze the text data
within the corpus.
"""
import os
import re
import tiktoken
from common.utils import TerminalColors
from corpus.schemas import CorpusItem

# --- Utils --- 

def _get_token_count(text: str) -> int:
    """
    Get the number of tokens in a text string.
    """
    encoding = tiktoken.get_encoding("o200k_base")
    tokens = encoding.encode(text)
    return len(tokens)

# --- Processing Functions ---

def _load_file(file_name: str) -> list[CorpusItem]:
    """
    Load a file and return a list of CorpusItems.

    Args:
        file_name (str): The name of the file to load.

    Returns:
        list[CorpusItem]: The loaded corpus items.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Clean comments
    cleaned = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)

    # Clean trailing spaces
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned, flags=re.MULTILINE)

    # Clear separators
    cleaned = re.sub(r"---", " ", cleaned, flags=re.DOTALL)
    
    # Extract Sections
    sections = re.findall(r"<section>(.*?)</section>", cleaned, re.DOTALL)

    # Load content within sections into CorpusItems
    corpus_items = []
    for section in sections:
        id = re.findall(r"<id>(.*?)</id>", section, re.DOTALL)
        header = re.findall(r"<header>(.*?)</header>", section, re.DOTALL)
        context = re.findall(r"<context>(.*?)</context>", section, re.DOTALL)
        document = re.findall(r"<document>(.*?)</document>", section, re.DOTALL)

        # Create a CorpusItem from the extracted content
        corpus_item = CorpusItem(
            id=id[0],
            header=header[0],
            context=context[0],
            document=document[0],
            embedding=[0.0]   # Placeholder for embedding
        )
        corpus_items.append(corpus_item)

    return corpus_items

def _analyse_corpus_item(corpus_item: CorpusItem) -> dict:
    """
    Analyse a single CorpusItem and return 
    relevant metrics.

    Args:
        corpus_item (CorpusItem): The CorpusItem to 
        analyse.

    Returns:
        dict: A dictionary containing analysis 
        results.
    """
    token_count = _get_token_count(corpus_item.document) + \
                  _get_token_count(corpus_item.context)
    print(
        f"{TerminalColors.blue}"
        f"{corpus_item.id}"
        f"{TerminalColors.reset}"
    )
    print(
        f"  Token count: {token_count}"
    )
    analysis = {
        "id": corpus_item.id,
        "token_count": token_count
    }
    return analysis

if __name__ == "__main__":
    """
    Main entry point for corpus
    analysis.
    """
    files = [
        "documents/personal.md",
        "documents/education.md",
        "documents/skills.md",
        "documents/projects.md",
        "documents/experience.md",
        "documents/meta_reflection.md",
    ]

    corpus_tokens = 0
    
    for file in files:
        print(
            f"{TerminalColors.green}"
            f"Processing file: {file} ..."
            f"{TerminalColors.reset}"
        )
        corpus_items = _load_file(file)
        analysis = [
            _analyse_corpus_item(item) 
            for item in corpus_items
        ]

        # Get summary statistics
        total_tokens = sum(
            item['token_count'] 
            for item in analysis
        )
        corpus_tokens += total_tokens
        print("\nSummary Statistics:")
        print(f"Total tokens: {total_tokens}")
        print("-" * 20)

    print(f"\nTotal corpus tokens: {corpus_tokens}")