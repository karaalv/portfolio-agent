"""Verify telemetry lifecycle and capture without network calls."""

import threading
from unittest.mock import AsyncMock, Mock

import pytest

from exceptions.posthog import PostHogException
from posthog_client import config, error_tracking

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_client(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Keep every test independent of credentials and live clients."""
	monkeypatch.setattr(config, '_posthog_client', None)
	monkeypatch.setattr(config, 'start_logging', Mock())
	monkeypatch.setattr(config, 'stop_logging', AsyncMock())
	monkeypatch.setenv('POSTHOG_API_KEY', ' test-project-key ')
	monkeypatch.setenv('POSTHOG_HOST', ' https://example.com ')
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')


@pytest.mark.parametrize('name', ['POSTHOG_API_KEY', 'POSTHOG_HOST'])
@pytest.mark.parametrize('value', [None, '', '   '])
def test_start_requires_both_settings(
	monkeypatch: pytest.MonkeyPatch,
	name: str,
	value: str | None,
) -> None:
	"""Reject missing/blank settings before constructing the SDK."""
	create = Mock()
	monkeypatch.setattr(config, 'Posthog', create)
	if value is None:
		monkeypatch.delenv(name)
	else:
		monkeypatch.setenv(name, value)
	with pytest.raises(PostHogException, match=name) as caught:
		config.start_posthog_client()
	assert caught.value.scope == 'posthog'
	create.assert_not_called()
	with pytest.raises(PostHogException, match='not started'):
		config.get_posthog_client()


def test_start_reuses_client_and_trims_settings(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Initialise once without automatic exception hooks."""
	client = Mock()
	create = Mock(return_value=client)
	monkeypatch.setattr(config, 'Posthog', create)
	config.start_posthog_client()
	monkeypatch.delenv('POSTHOG_API_KEY')
	config.start_posthog_client()
	assert config.get_posthog_client() is client
	create.assert_called_once_with(
		project_api_key='test-project-key',
		host='https://example.com',
		enable_exception_autocapture=False,
	)


async def test_shutdown_detaches_before_cleanup_in_thread(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Drain once outside the event loop with a strict getter."""
	loop_thread = threading.get_ident()

	def shutdown() -> None:
		assert threading.get_ident() != loop_thread
		with pytest.raises(PostHogException, match='not started'):
			config.get_posthog_client()

	client = Mock(shutdown=Mock(side_effect=shutdown))
	monkeypatch.setattr(config, '_posthog_client', client)
	await config.stop_posthog_client()
	await config.stop_posthog_client()
	client.shutdown.assert_called_once_with()


async def test_failed_shutdown_leaves_client_unavailable(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Do not return a partly stopped client after cleanup fails."""
	client = Mock()
	client.shutdown.side_effect = RuntimeError('shutdown failed')
	monkeypatch.setattr(config, '_posthog_client', client)
	with pytest.raises(RuntimeError, match='shutdown failed'):
		await config.stop_posthog_client()
	with pytest.raises(PostHogException, match='not started'):
		config.get_posthog_client()


def test_testing_capture_does_not_access_client(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Skip telemetry even when no client or credentials exist."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	get_client = Mock(side_effect=AssertionError('client accessed'))
	monkeypatch.setattr(
		error_tracking, 'get_posthog_client', get_client
	)
	error_tracking.capture_exception(ValueError('invalid'), None, {})
	get_client.assert_not_called()


@pytest.mark.parametrize('user_id', ['visitor-123', None])
def test_capture_forwards_original_exception_and_identity(
	monkeypatch: pytest.MonkeyPatch,
	user_id: str | None,
) -> None:
	"""Preserve the exception object and supplied properties."""
	client = Mock()
	monkeypatch.setattr(config, '_posthog_client', client)
	exc = ValueError('invalid')
	properties = {'request_id': 'request-123'}
	error_tracking.capture_exception(exc, user_id, properties)
	kwargs: dict[str, object] = {'properties': properties}
	if user_id is not None:
		kwargs['distinct_id'] = user_id
	client.capture_exception.assert_called_once_with(exc, **kwargs)


def test_capture_does_not_hide_missing_startup() -> None:
	"""Surface genuine lifecycle mistakes outside testing."""
	with pytest.raises(PostHogException, match='not started'):
		error_tracking.capture_exception(
			ValueError('invalid'), None, {}
		)


def test_capture_does_not_suppress_sdk_errors(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Leave application-level error policy to the caller."""
	client = Mock()
	client.capture_exception.side_effect = RuntimeError(
		'capture failed'
	)
	monkeypatch.setattr(config, '_posthog_client', client)
	with pytest.raises(RuntimeError, match='capture failed'):
		error_tracking.capture_exception(
			ValueError('invalid'), None, {}
		)
