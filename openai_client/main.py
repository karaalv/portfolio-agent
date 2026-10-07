"""
Main module for interacting with the OpenAI API.
"""

from collections.abc import AsyncGenerator
from typing import TypeVar

from openai.types.responses import (
	ResponseInputParam,
	ResponseStreamEvent,
	ToolParam,
)
from pydantic import BaseModel

from exceptions.openai import OpenAIException
from openai_client.config import get_openai_client
from openai_client.limits import (
	get_openai_embedding_limiter,
	get_openai_response_limiter,
	get_openai_response_timeout,
	get_openai_semaphore,
)
from openai_client.model_settings import (
	OpenAILanguageModelReasoning,
	OpenAILanguageModelVerbosity,
)
from openai_client.models import (
	OpenAIEmbeddingModel,
	OpenAILanguageModel,
)

# Generic type for response models
T = TypeVar('T', bound=BaseModel)

# --- Embedding Functionality ---


async def get_embedding(
	input: str,
	model: OpenAIEmbeddingModel = (
		OpenAIEmbeddingModel.TEXT_EMBEDDING_3_LARGE
	),
) -> list[float]:
	"""
	Get the embedding for the given
	input using the specified OpenAI
	embedding model.
	"""
	client = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_embedding_limiter()
	timeout = get_openai_response_timeout()

	async with limiter:
		async with semaphore:
			response = await client.embeddings.create(
				model=model.value, input=input, timeout=timeout
			)

			if not response.data or not response.data[0].embedding:
				raise OpenAIException(
					message=(
						'Failed to retrieve embedding'
						'from OpenAI response.'
					),
					module='openai_client.main',
					operation='get_embedding',
				)
	return response.data[0].embedding


# --- Language Model Functionality ---


async def text_response(
	system_prompt: str,
	user_prompt: str,
	model: OpenAILanguageModel = OpenAILanguageModel.GPT_6_LUNA,
	reasoning: OpenAILanguageModelReasoning = (
		OpenAILanguageModelReasoning.MEDIUM
	),
	verbosity: OpenAILanguageModelVerbosity = (
		OpenAILanguageModelVerbosity.MEDIUM
	),
) -> str:
	"""
	Generates a text response from the OpenAI language
	model based on the system and user prompts.
	"""
	client = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	timeout = get_openai_response_timeout()

	async with limiter:
		async with semaphore:
			response = await client.responses.create(
				model=model,
				instructions=system_prompt,
				input=user_prompt,
				reasoning={'effort': reasoning.value},
				text={'verbosity': verbosity.value},
				timeout=timeout,
			)

			text = response.output_text.strip()
			if not text:
				raise OpenAIException(
					message=(
						'Failed to retrieve text response'
						'from OpenAI response.'
					),
					module='openai_client.main',
					operation='text_response',
				)
	return text


async def structured_response(
	system_prompt: str,
	user_prompt: str,
	response_format: type[T],
	model: OpenAILanguageModel = OpenAILanguageModel.GPT_6_1_SOL,
	reasoning: OpenAILanguageModelReasoning = (
		OpenAILanguageModelReasoning.MEDIUM
	),
) -> T:
	"""
	Generates a structured response from the OpenAI language
	model based on the system and user prompts, and parses it
	into the specified response format.
	"""

	client = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	timeout = get_openai_response_timeout()

	async with limiter:
		async with semaphore:
			response = await client.responses.parse(
				model=model,
				instructions=system_prompt,
				input=user_prompt,
				reasoning={'effort': reasoning.value},
				text_format=response_format,
				timeout=timeout,
			)

			parsed_response = response.output_parsed
			if not parsed_response:
				raise OpenAIException(
					message=(
						'Failed to retrieve structured response'
						'from OpenAI response.'
					),
					module='openai_client.main',
					operation='structured_response',
				)

			# Check if the parsed response matches
			# expected schema
			if not isinstance(parsed_response, response_format):
				raise OpenAIException(
					message=(
						'Parsed response does not'
						'match the expected schema.'
					),
					module='openai_client.main',
					operation='structured_response',
				)
	return parsed_response


async def stream_agent_response(
	system_prompt: str,
	input: ResponseInputParam,
	model: OpenAILanguageModel = OpenAILanguageModel.GPT_6_1_SOL,
	reasoning: OpenAILanguageModelReasoning = (
		OpenAILanguageModelReasoning.MEDIUM
	),
	tools: list[ToolParam] | None = None,
	verbosity: OpenAILanguageModelVerbosity = (
		OpenAILanguageModelVerbosity.MEDIUM
	),
) -> AsyncGenerator[ResponseStreamEvent, None]:
	"""
	Yield response events while holding the OpenAI concurrency permit.
	Close the generator if consumption stops before the stream ends.
	"""
	client = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	timeout = get_openai_response_timeout()

	async with limiter, semaphore:
		stream = await client.responses.create(
			model=model,
			instructions=system_prompt,
			input=input,
			tools=tools or [],
			reasoning={'effort': reasoning.value},
			text={'verbosity': verbosity.value},
			timeout=timeout,
			stream=True,
			store=False,
			include=['reasoning.encrypted_content'],
		)
		async with stream:
			async for event in stream:
				yield event
