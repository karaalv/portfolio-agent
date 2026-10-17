"""Configure Python logging for OTLP export to PostHog.

This module only owns the handler, provider and exporter setup that
routes application logs to PostHog. Logging helpers remain independent
of this transport. OpenTelemetry's experimental logs API requires the
private ``_logs`` imports documented by PostHog.
"""

import asyncio
import logging
from os import getenv

from opentelemetry.exporter.otlp.proto.http._log_exporter import (
	OTLPLogExporter,
)
from opentelemetry.instrumentation.logging.handler import (
	LoggingHandler,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from shared.logging.logger import LOGGER_NAME

_logger_provider: LoggerProvider | None = None
_logging_handler: LoggingHandler | None = None


def start_logging(api_key: str, host: str) -> None:
	"""Attach one batched exporter in development and production."""
	global _logger_provider, _logging_handler
	environment = getenv('PORTFOLIO_AGENT_ENV')
	if environment not in {'development', 'production'}:
		return
	if _logger_provider is not None:
		return
	provider = LoggerProvider(
		resource=Resource.create(
			{
				'service.name': LOGGER_NAME,
				'deployment.environment.name': environment,
			}
		),
		shutdown_on_exit=False,
	)
	try:
		exporter = OTLPLogExporter(
			endpoint=f'{host.rstrip("/")}/i/v1/logs',
			headers={'Authorization': f'Bearer {api_key}'},
		)
		provider.add_log_record_processor(
			BatchLogRecordProcessor(exporter)
		)
		handler = LoggingHandler(
			level=logging.INFO,
			logger_provider=provider,
			log_code_attributes=True,
		)
		logging.getLogger(LOGGER_NAME).addHandler(handler)
	except BaseException:
		provider.shutdown()
		raise
	_logger_provider = provider
	_logging_handler = handler


async def stop_logging() -> None:
	"""Detach the export handler and drain logs off the event loop."""
	global _logger_provider, _logging_handler
	provider = _logger_provider
	handler = _logging_handler
	_logger_provider = None
	_logging_handler = None
	if handler is not None:
		logging.getLogger(LOGGER_NAME).removeHandler(handler)
	if provider is None:
		return

	def shutdown() -> None:
		try:
			provider.shutdown()
		finally:
			if handler is not None:
				handler.close()

	await asyncio.to_thread(shutdown)
