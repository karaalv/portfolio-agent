"""Configure RAG models, history and vector retrieval limits."""

from openai_client.models import OpenAILanguageModel

INPUT_REFINER_MODEL = OpenAILanguageModel.GPT_6_LUNA
QUERY_PLANNER_MODEL = OpenAILanguageModel.GPT_6_1_SOL
CONTEXT_REFINER_MODEL = OpenAILanguageModel.GPT_6_LUNA
HISTORY_WINDOW = 10
MAX_QUERIES = 3
RETRIEVAL_LIMIT = 3
RETRIEVAL_THRESHOLD = 0.6
CANDIDATE_MULTIPLIER = 25
VECTOR_INDEX_NAME = 'corpus_vector_index'
VECTOR_PATH = 'embedding'
