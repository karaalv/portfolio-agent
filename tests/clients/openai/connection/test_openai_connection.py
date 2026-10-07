"""Check OpenAI access without generating tokens."""

import pytest
from openai import AsyncOpenAI

pytestmark = [
	pytest.mark.integration,
	pytest.mark.asyncio(loop_scope='package'),
]


async def test_openai_is_connected(
	openai_client: AsyncOpenAI,
) -> None:
	"""Require an authenticated model-list operation."""
	models = await openai_client.models.list()
	assert models.data
	assert all(model.id for model in models.data)
