"""Verify shared logging records without a remote exporter."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from shared.logging import (
	log_critical,
	log_debug,
	log_error,
	log_info,
	log_warning,
)
from shared.logging.logger import LOGGER_NAME

pytestmark = pytest.mark.unit


@pytest.fixture
def records() -> Iterator[list[logging.LogRecord]]:
	"""Observe the application logger without root propagation."""
	received: list[logging.LogRecord] = []

	class Recorder(logging.Handler):
		def emit(self, record: logging.LogRecord) -> None:
			received.append(record)

	logger = logging.getLogger(LOGGER_NAME)
	previous_level = logger.level
	handler = Recorder()
	logger.addHandler(handler)
	logger.setLevel(logging.DEBUG)
	try:
		yield received
	finally:
		logger.removeHandler(handler)
		logger.setLevel(previous_level)
		handler.close()


@pytest.mark.parametrize(
	('helper', 'level'),
	[
		(log_debug, logging.DEBUG),
		(log_info, logging.INFO),
		(log_warning, logging.WARNING),
		(log_error, logging.ERROR),
		(log_critical, logging.CRITICAL),
	],
)
def test_helpers_preserve_fields_and_caller(records, helper, level):
	"""Keep native field types and report the calling module."""
	extra = {'user_id': 'visitor', 'count': 3, 'successful': True}
	helper('Operation finished', extra)
	assert len(records) == 1
	record = records[0]
	assert record.name == LOGGER_NAME
	assert record.levelno == level
	assert record.getMessage() == 'Operation finished'
	assert record.count == 3
	assert record.successful is True
	assert record.user_id == 'visitor'
	assert Path(record.pathname) == Path(__file__)
	assert (
		record.funcName == 'test_helpers_preserve_fields_and_caller'
	)
	assert extra == {
		'user_id': 'visitor',
		'count': 3,
		'successful': True,
	}


@pytest.mark.parametrize('helper', [log_error, log_critical])
def test_failure_helpers_preserve_supplied_traceback(records, helper):
	"""Retain the original traceback even outside an except block."""
	try:
		raise ValueError('invalid')
	except ValueError as error:
		exc = error
	helper('Operation failed', exc=exc)
	assert records[0].exc_info is not None
	assert records[0].exc_info[1] is exc
	assert records[0].exc_info[2] is exc.__traceback__


def test_testing_keeps_local_logs(
	records, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""Do not suppress normal logging in the testing environment."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	log_info('Local test message')
	assert len(records) == 1
	assert records[0].getMessage() == 'Local test message'
