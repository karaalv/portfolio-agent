"""Exercise the actual logging pipeline with an in-memory exporter."""

import logging
import threading
from collections.abc import AsyncIterator
from unittest.mock import Mock

import pytest
from opentelemetry._logs import get_logger_provider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter

from posthog_client import _logging, config
from shared.logging import log_error, log_info
from shared.logging.logger import LOGGER_NAME

pytestmark = pytest.mark.unit


class RecordingExporter(InMemoryLogRecordExporter):
	"""Record drained logs and the thread that closes the exporter."""

	def shutdown(self) -> None:
		self.drained_logs = self.get_finished_logs()
		self.shutdown_thread = threading.get_ident()
		super().shutdown()


@pytest.fixture(autouse=True)
async def isolated_pipeline(
	monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[RecordingExporter, Mock]]:
	"""Guarantee cleanup and keep every export in memory."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'development')
	exporter = RecordingExporter()
	factory = Mock(return_value=exporter)
	monkeypatch.setattr(_logging, 'OTLPLogExporter', factory)
	try:
		yield exporter, factory
	finally:
		await _logging.stop_logging()


async def test_pipeline_preserves_structured_fields_and_exception(
	isolated_pipeline,
):
	"""Bridge helper records through the real batched processor."""
	global_provider = get_logger_provider()
	_logging.start_logging('test-project-key', 'https://example.com/')
	_logging.start_logging('test-project-key', 'https://example.com/')
	exporter, factory = isolated_pipeline
	factory.assert_called_once_with(
		endpoint='https://example.com/i/v1/logs',
		headers={'Authorization': 'Bearer test-project-key'},
	)
	log_info(
		'Maintenance completed', {'count': 3, 'successful': True}
	)
	try:
		raise ValueError('invalid')
	except ValueError as exc:
		log_error(
			'Operation failed', {'request_id': 'request-1'}, exc=exc
		)
	provider = _logging._logger_provider
	assert provider is not None
	assert provider.force_flush()
	logs = exporter.get_finished_logs()
	assert len(logs) == 2
	assert logs[0].log_record.body == 'Maintenance completed'
	attributes = logs[0].log_record.attributes
	assert attributes is not None
	assert attributes['count'] == 3
	assert attributes['successful'] is True
	assert logs[0].resource.attributes['service.name'] == LOGGER_NAME
	assert (
		logs[0].resource.attributes['deployment.environment.name']
		== 'development'
	)
	error_attributes = logs[1].log_record.attributes
	assert error_attributes is not None
	assert error_attributes['request_id'] == 'request-1'
	assert error_attributes['exception.type'] == 'ValueError'
	assert (
		'ValueError: invalid'
		in error_attributes['exception.stacktrace']
	)
	assert get_logger_provider() is global_provider


@pytest.mark.parametrize('environment', ['testing', None])
def test_inactive_environments_do_not_construct_exporter(
	monkeypatch: pytest.MonkeyPatch,
	environment: str | None,
	isolated_pipeline,
) -> None:
	"""Skip export in testing and without an environment."""
	if environment is None:
		monkeypatch.delenv('PORTFOLIO_AGENT_ENV')
	else:
		monkeypatch.setenv('PORTFOLIO_AGENT_ENV', environment)
	_logging.start_logging('test-project-key', 'https://example.com')
	log_info('Local operation')
	isolated_pipeline[1].assert_not_called()
	assert _logging._logger_provider is None
	assert _logging._logging_handler is None


async def test_shutdown_drains_once_in_thread_and_allows_restart(
	isolated_pipeline,
):
	"""Detach the export handler while retaining local logging."""
	logger = logging.getLogger(LOGGER_NAME)
	original_handlers = list(logger.handlers)
	loop_thread = threading.get_ident()
	_logging.start_logging('test-project-key', 'https://example.com')
	log_info('Queued before shutdown')
	exporter = isolated_pipeline[0]
	await _logging.stop_logging()
	await _logging.stop_logging()
	assert len(exporter.drained_logs) == 1
	assert exporter.shutdown_thread != loop_thread
	assert logger.handlers == original_handlers
	assert _logging._logger_provider is None
	assert _logging._logging_handler is None
	_logging.start_logging('test-project-key', 'https://example.com')
	assert _logging._logger_provider is not None
	assert len(logger.handlers) == len(original_handlers) + 1


async def test_sdk_shutdown_failure_still_drains_logs(
	monkeypatch: pytest.MonkeyPatch,
	isolated_pipeline,
) -> None:
	"""Drain logs even when event client shutdown fails."""
	client = Mock()
	client.shutdown.side_effect = RuntimeError('SDK shutdown failed')
	monkeypatch.setattr(config, '_posthog_client', client)
	_logging.start_logging('test-project-key', 'https://example.com')
	log_info('Queued before SDK shutdown')
	exporter = isolated_pipeline[0]
	with pytest.raises(RuntimeError, match='SDK shutdown failed'):
		await config.stop_posthog_client()
	assert len(exporter.drained_logs) == 1
	assert _logging._logger_provider is None


async def test_failed_logging_startup_is_cleaned_up(
	monkeypatch: pytest.MonkeyPatch,
	isolated_pipeline,
) -> None:
	"""Release partially started telemetry through normal cleanup."""
	monkeypatch.setenv('POSTHOG_API_KEY', 'test-project-key')
	monkeypatch.setenv('POSTHOG_HOST', 'https://example.com')
	monkeypatch.setattr(config, '_posthog_client', None)
	client = Mock()
	monkeypatch.setattr(config, 'Posthog', Mock(return_value=client))
	isolated_pipeline[1].side_effect = RuntimeError('setup failed')
	with pytest.raises(RuntimeError, match='setup failed'):
		config.start_posthog_client()
	await config.stop_posthog_client()
	client.shutdown.assert_called_once_with()
	assert _logging._logger_provider is None
	assert _logging._logging_handler is None
