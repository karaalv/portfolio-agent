"""Emit application logs independently of their export destination."""

import logging
from typing import Any

LOGGER_NAME = 'portfolio_agent'
_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(logging.INFO)
_logger.propagate = False
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
	logging.Formatter('%(levelname)s %(name)s: %(message)s')
)
_logger.addHandler(_console_handler)


def log_debug(
	message: str, extra: dict[str, Any] | None = None
) -> None:
	"""Log diagnostic details when DEBUG is enabled."""
	_logger.debug(message, extra=extra, stacklevel=2)


def log_info(
	message: str, extra: dict[str, Any] | None = None
) -> None:
	"""Log a normal operational outcome."""
	_logger.info(message, extra=extra, stacklevel=2)


def log_warning(
	message: str, extra: dict[str, Any] | None = None
) -> None:
	"""Log an unexpected but recoverable outcome."""
	_logger.warning(message, extra=extra, stacklevel=2)


def log_error(
	message: str,
	extra: dict[str, Any] | None = None,
	*,
	exc: BaseException | None = None,
) -> None:
	"""Log a failure and optionally preserve its traceback."""
	_logger.error(message, extra=extra, exc_info=exc, stacklevel=2)


def log_critical(
	message: str,
	extra: dict[str, Any] | None = None,
	*,
	exc: BaseException | None = None,
) -> None:
	"""Log a service-level failure and optional traceback."""
	_logger.critical(message, extra=extra, exc_info=exc, stacklevel=2)
