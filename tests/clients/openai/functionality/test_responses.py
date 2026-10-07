"""Exercise OpenAI wrappers against the testing client."""

import json
import math
from contextlib import aclosing

import pytest
from openai import AsyncOpenAI
from openai.types.responses import Response, ToolParam

from openai_client.main import (
	get_embedding,
	stream_agent_response,
	structured_response,
	text_response,
)
from openai_client.model_settings import (
	OpenAILanguageModelReasoning,
	OpenAILanguageModelVerbosity,
)
from openai_client.models import OpenAILanguageModel
from tests.schemas.openai import CapitalResponse

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_embedding(openai_client: AsyncOpenAI) -> None:
	"""Return a finite vector with the expected dimensions."""
	embedding = await get_embedding('Portfolio client test.')
	assert len(embedding) == 3072
	assert all(math.isfinite(value) for value in embedding)
	assert any(value != 0 for value in embedding)


async def test_text_response(openai_client: AsyncOpenAI) -> None:
	"""Answer a fixed question without external tools."""
	response = await text_response(
		system_prompt='Answer the question briefly.',
		user_prompt='What is the capital of France?',
		model=OpenAILanguageModel.GPT_6_LUNA,
		reasoning=OpenAILanguageModelReasoning.LOW,
		verbosity=OpenAILanguageModelVerbosity.LOW,
	)
	assert 'paris' in response.casefold()


async def test_structured_response(
	openai_client: AsyncOpenAI,
) -> None:
	"""Parse a fixed answer into the supplied Pydantic schema."""
	response = await structured_response(
		system_prompt='Answer using the supplied schema.',
		user_prompt='Give France and its capital.',
		response_format=CapitalResponse,
		model=OpenAILanguageModel.GPT_6_LUNA,
		reasoning=OpenAILanguageModelReasoning.LOW,
	)
	assert isinstance(response, CapitalResponse)
	assert response.capital == 'Paris'


async def test_stream_text(openai_client: AsyncOpenAI) -> None:
	"""Check streamed text against completed output."""
	stream = stream_agent_response(
		system_prompt='Answer briefly without tools.',
		input=[{'role': 'user', 'content': 'Say hello.'}],
		model=OpenAILanguageModel.GPT_6_LUNA,
		reasoning=OpenAILanguageModelReasoning.LOW,
		verbosity=OpenAILanguageModelVerbosity.LOW,
	)
	deltas: list[str] = []
	completed: Response | None = None
	async with aclosing(stream) as events:
		async for event in events:
			if event.type == 'response.output_text.delta':
				deltas.append(event.delta)
			elif event.type == 'response.completed':
				completed = event.response
			elif event.type in {
				'error',
				'response.failed',
				'response.incomplete',
			}:
				pytest.fail(
					f'Stream did not complete: {event.type}'
				)
	assert completed is not None
	assert completed.status == 'completed'
	assert deltas
	assert ''.join(deltas) == completed.output_text


async def test_stream_function_call(
	openai_client: AsyncOpenAI,
) -> None:
	"""Return function calls with valid arguments and IDs."""
	tools: list[ToolParam] = [
		{
			'type': 'function',
			'name': 'echo',
			'description': 'Echo the given value.',
			'strict': True,
			'parameters': {
				'type': 'object',
				'properties': {'value': {'type': 'string'}},
				'required': ['value'],
				'additionalProperties': False,
			},
		}
	]
	stream = stream_agent_response(
		system_prompt='Always invoke echo for the given value.',
		input=[
			{'role': 'user', 'content': 'Echo portfolio-test.'}
		],
		tools=tools,
		model=OpenAILanguageModel.GPT_6_LUNA,
		reasoning=OpenAILanguageModelReasoning.LOW,
	)
	completed: Response | None = None
	async with aclosing(stream) as events:
		async for event in events:
			if event.type == 'response.completed':
				completed = event.response
			elif event.type in {
				'error',
				'response.failed',
				'response.incomplete',
			}:
				pytest.fail(
					f'Stream did not complete: {event.type}'
				)
	assert completed is not None
	calls = [
		item
		for item in completed.output
		if item.type == 'function_call'
	]
	assert calls
	for call in calls:
		assert call.name == 'echo'
		assert call.call_id
		assert json.loads(call.arguments) == {
			'value': 'portfolio-test'
		}
