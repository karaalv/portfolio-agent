"""Check correlation, severity and exception reporting failures."""

import logging
from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from exceptions.core import PortfolioAgentException
from posthog_client import error_tracking
from shared.logging.logger import LOGGER_NAME

pytestmark = pytest.mark.unit


@pytest.fixture
def logs(
	caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
	"""Observe records from the non-propagating application logger."""
	logger = logging.getLogger(LOGGER_NAME)
	logger.addHandler(caplog.handler)
	try:
		yield caplog
	finally:
		logger.removeHandler(caplog.handler)


def test_report_links_user_and_session_and_captures_once(
	monkeypatch, logs
):
	"""Keep original exception metadata without reserved log keys."""
	capture = Mock()
	monkeypatch.setattr(error_tracking, 'capture_exception', capture)
	exc = PortfolioAgentException('failed', 'api', 'example', 'read')
	for _ in range(2):
		error_tracking.report_exception(
			exc,
			'operation_failed',
			{},
			user_id='server-user',
			posthog_session_id='browser-session',
		)
	capture.assert_called_once()
	assert capture.call_args.args[:2] == (exc, 'server-user')
	properties = capture.call_args.args[2]
	assert properties['module'] == 'example'
	assert properties['scope'] == 'api'
	assert properties['posthogDistinctId'] == 'server-user'
	assert properties['sessionId'] == 'browser-session'
	assert properties['$session_id'] == 'browser-session'
	assert len(logs.records) == 1
	assert logs.records[0].exception_module == 'example'
	assert logs.records[0].levelno == logging.ERROR


def test_capture_failure_does_not_replace_original_error(
	monkeypatch, logs
):
	"""Keep export failures local and avoid recursive capture."""
	capture = Mock(side_effect=RuntimeError('telemetry offline'))
	monkeypatch.setattr(error_tracking, 'capture_exception', capture)
	exc = ValueError('original failure')
	error_tracking.report_exception(exc, 'operation_failed', {})
	assert [record.getMessage() for record in logs.records] == [
		'operation_failed',
		'telemetry_capture_failed',
	]
	capture.assert_called_once()
