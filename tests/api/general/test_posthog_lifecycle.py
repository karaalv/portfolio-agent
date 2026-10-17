"""Check PostHog participation in API startup and cleanup."""

from unittest.mock import AsyncMock, Mock, call

import pytest

from api.lifecycle import config

pytestmark = pytest.mark.unit


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch) -> Mock:
	"""Replace external services while retaining API ordering."""
	order = Mock()
	for name in (
		'load_environment_variables',
		'start_posthog_client',
		'start_mongo_client',
		'start_openai_client',
		'start_websocket_registry',
		'stop_websocket_registry',
		'stop_openai_client',
		'stop_mongo_client',
		'stop_posthog_client',
	):
		is_async = name.startswith('stop_') or name in {
			'start_mongo_client',
			'start_websocket_registry',
		}
		function = AsyncMock() if is_async else Mock()
		monkeypatch.setattr(config, name, function)
		order.attach_mock(function, name)
	return order


@pytest.mark.parametrize(
	'environment', ['development', 'production', 'testing']
)
async def test_posthog_only_starts_in_active_environments(
	lifecycle: Mock,
	monkeypatch: pytest.MonkeyPatch,
	environment: str,
) -> None:
	"""Start telemetry after env loading and before other clients."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', environment)
	await config.start_api_lifecycle()
	expected = [call.load_environment_variables()]
	if environment != 'testing':
		expected.append(call.start_posthog_client())
	expected.extend(
		[
			call.start_mongo_client(),
			call.start_openai_client(),
			call.start_websocket_registry(),
		]
	)
	assert lifecycle.mock_calls == expected


@pytest.mark.parametrize(
	'failed_service',
	[
		None,
		'stop_websocket_registry',
		'stop_openai_client',
		'stop_mongo_client',
	],
)
async def test_posthog_stops_last_even_if_cleanup_fails(
	lifecycle: Mock,
	failed_service: str | None,
) -> None:
	"""Attempt telemetry drain after every other client cleanup."""
	if failed_service:
		getattr(lifecycle, failed_service).side_effect = RuntimeError(
			'cleanup failed'
		)
		with pytest.raises(RuntimeError, match='cleanup failed'):
			await config.stop_api_lifecycle()
	else:
		await config.stop_api_lifecycle()
	assert lifecycle.mock_calls == [
		call.stop_websocket_registry(),
		call.stop_openai_client(),
		call.stop_mongo_client(),
		call.stop_posthog_client(),
	]
