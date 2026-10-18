"""Configure Python logging and tracing for OTLP export to PostHog.

This module only owns the handler, provider and exporter setup that
routes application telemetry to PostHog. Helpers remain independent
of this transport. OpenTelemetry's experimental logs API requires the
private ``_logs`` imports documented by PostHog.
"""

import asyncio
import logging
from os import getenv

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
	OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
	OTLPSpanExporter,
)
from opentelemetry.instrumentation.logging.handler import (
	LoggingHandler,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from shared.logging.logger import LOGGER_NAME

_logger_provider: LoggerProvider | None = None
_logging_handler: LoggingHandler | None = None
_tracer_provider: TracerProvider | None = None


def get_tracer() -> trace.Tracer:
	"""Return a tracer from the lifecycle-owned provider."""
	if _tracer_provider is None:
		return trace.NoOpTracer()
	return _tracer_provider.get_tracer(LOGGER_NAME)


def start_logging(api_key: str, host: str) -> None:
	"""Attach batched log and span exporters in dev and production."""
	global _logger_provider, _logging_handler, _tracer_provider
	environment = getenv('PORTFOLIO_AGENT_ENV')
	if environment not in {'development', 'production'}:
		return
	if _logger_provider is not None:
		return
	resource = Resource.create(
		{
			'service.name': LOGGER_NAME,
			'deployment.environment.name': environment,
		}
	)
	provider = LoggerProvider(
		resource=resource,
		shutdown_on_exit=False,
	)
	tracer_provider = TracerProvider(
		resource=resource, shutdown_on_exit=False
	)
	try:
		tracer_provider.add_span_processor(
			BatchSpanProcessor(
				OTLPSpanExporter(
					endpoint=f'{host.rstrip("/")}/i/v1/traces',
					headers={'Authorization': f'Bearer {api_key}'},
				)
			)
		)
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
		try:
			tracer_provider.shutdown()
		finally:
			provider.shutdown()
		raise
	_logger_provider = provider
	_logging_handler = handler
	_tracer_provider = tracer_provider


async def stop_logging() -> None:
	"""Detach exporters and drain telemetry off the event loop."""
	global _logger_provider, _logging_handler, _tracer_provider
	provider = _logger_provider
	handler = _logging_handler
	tracer_provider = _tracer_provider
	_logger_provider = None
	_logging_handler = None
	_tracer_provider = None
	if handler is not None:
		logging.getLogger(LOGGER_NAME).removeHandler(handler)
	if provider is None and tracer_provider is None:
		return

	def shutdown() -> None:
		try:
			if tracer_provider is not None:
				tracer_provider.shutdown()
		finally:
			try:
				if provider is not None:
					provider.shutdown()
			finally:
				if handler is not None:
					handler.close()

	await asyncio.to_thread(shutdown)
