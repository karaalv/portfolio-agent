"""Create application spans with optional server-owned identity."""

from collections.abc import Iterator, Mapping, Generator
from contextlib import contextmanager
from os import getenv

from opentelemetry.trace import NoOpTracer, Span, SpanKind
from opentelemetry.util.types import AttributeValue

from posthog_client._logging import get_tracer


@contextmanager
def start_span(
	name: str,
	user_id: str | None = None,
	session_id: str | None = None,
	*,
	attributes: Mapping[str, AttributeValue | None] | None = None,
	kind: SpanKind = SpanKind.INTERNAL,
) -> Generator[Span, None, None]:
	"""Yield an active span; omit absent identity and metadata.

	Children inherit OTel context across awaits and new asyncio tasks.
	Tests and unstarted telemetry use non-recording spans. Identity
	comes from verified server context.
	"""
	metadata = {
		key: value
		for key, value in (attributes or {}).items()
		if value is not None
	}
	if user_id is not None:
		metadata.update(user_id=user_id, posthogDistinctId=user_id)
	if session_id is not None:
		metadata.update(session_id=session_id, sessionId=session_id)
	tracer = get_tracer()
	if getenv('PORTFOLIO_AGENT_ENV') not in {
		'development',
		'production',
	}:
		tracer = NoOpTracer()
	with tracer.start_as_current_span(
		name, attributes=metadata, kind=kind
	) as span:
		yield span
