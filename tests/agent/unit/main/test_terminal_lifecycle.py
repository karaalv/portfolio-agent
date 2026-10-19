"""Verify terminal client ordering without live services."""

from unittest.mock import AsyncMock, Mock, call

import pytest

from tests.agent import agent_input

pytestmark = pytest.mark.unit


@pytest.fixture
def clients(monkeypatch):
	"""Replace terminal IO and service clients with local mocks."""
	order = Mock()
	for name in (
		'start_posthog_client',
		'start_mongo_client',
		'start_openai_client',
		'stop_openai_client',
		'stop_mongo_client',
		'stop_posthog_client',
	):
		function = (
			AsyncMock()
			if name.startswith('stop_')
			or name == 'start_mongo_client'
			else Mock()
		)
		monkeypatch.setattr(agent_input, name, function)
		order.attach_mock(function, name)
	monkeypatch.setattr(
		agent_input, 'load_environment_variables', Mock()
	)
	monkeypatch.setattr(
		agent_input,
		'is_mongo_connected',
		AsyncMock(return_value=True),
	)
	monkeypatch.setattr(
		agent_input, 'does_user_exist', AsyncMock(return_value=True)
	)
	monkeypatch.setattr(
		agent_input.Path, 'is_file', lambda path: True
	)
	monkeypatch.setattr('builtins.input', lambda prompt: 'exit')
	return order


@pytest.mark.parametrize(
	'environment', ['testing', 'development', 'staging', 'production']
)
async def test_terminal_telemetry_order(
	clients, monkeypatch, environment
):
	"""Start telemetry before OpenAI only in active environments."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', environment)
	await agent_input.main(user_id='visitor')
	expected = []
	if environment != 'testing':
		expected.append(call.start_posthog_client())
	expected.extend(
		[
			call.start_mongo_client(),
			call.start_openai_client(),
			call.stop_openai_client(),
			call.stop_mongo_client(),
			call.stop_posthog_client(),
		]
	)
	assert clients.mock_calls == expected


async def test_terminal_failed_startup_still_drains(
	clients, monkeypatch
):
	"""Retain the startup error and attempt every client shutdown."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')
	clients.start_openai_client.side_effect = RuntimeError('failed')
	with pytest.raises(RuntimeError, match='failed'):
		await agent_input.main(user_id='visitor')
	assert clients.mock_calls[-3:] == [
		call.stop_openai_client(),
		call.stop_mongo_client(),
		call.stop_posthog_client(),
	]
