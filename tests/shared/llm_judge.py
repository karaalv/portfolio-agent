"""Evaluate test outputs using the existing OpenAI client."""

from openai_client.main import structured_response
from openai_client.model_settings import (
	OpenAILanguageModelReasoning,
)
from openai_client.models import OpenAILanguageModel
from tests.schemas.judgement import LLMJudgement


async def llm_as_judge(
	system_prompt: str,
	user_prompt: str,
) -> LLMJudgement:
	"""Return a structured verdict for the supplied test rubric.

	The caller supplies the rubric and evaluation data, then
	asserts on the verdict. The OpenAI client must be started
	by the requesting integration package's client fixture.
	"""
	return await structured_response(
		system_prompt=system_prompt,
		user_prompt=user_prompt,
		response_format=LLMJudgement,
		model=OpenAILanguageModel.GPT_6_1_SOL,
		reasoning=OpenAILanguageModelReasoning.LOW,
	)
