"""Start production services on the ASGI client's loop."""

from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from agent.memory.deletion import delete_agent_memory
from api.config.cookies import get_cookie_domain
from api.utils.cors import get_allowed_origins
from api.websocket import get_websocket_registry
from schemas.security.monitoring.usage import UsageEntity
from security.monitoring.usage.deletion import (
	delete_usage_statistics,
)
from tests.shared.clients import load_test_environment
from users.deletion import delete_user


@pytest.fixture(scope='package')
def live_client() -> Iterator[TestClient]:
	"""Run the real application lifespan with testing settings."""
	with pytest.MonkeyPatch.context() as patch:
		load_test_environment(patch)
		from api.server import app

		origins = get_allowed_origins()
		assert origins, 'Testing CORS_ORIGINS must be configured.'
		domain = get_cookie_domain().lstrip('.')
		if '.' not in domain:
			# HTTPX rejects cookies scoped to a bare localhost.
			domain = 'portfolio.test'
			patch.setenv('COOKIE_DOMAIN', domain)
		with TestClient(
			app,
			base_url=f'https://{domain}',
			headers={'Origin': origins[0]},
		) as client:
			yield client


@pytest.fixture
def visitor_ids(live_client: TestClient) -> Iterator[list[str]]:
	"""Remove only identities created by the requesting test."""
	live_client.cookies.clear()
	identities: list[str] = []
	try:
		yield identities
	finally:
		assert live_client.portal is not None
		for user_id in identities:
			live_client.portal.call(
				get_websocket_registry().remove_user_connections,
				user_id,
			)
			live_client.portal.call(delete_agent_memory, user_id)
			live_client.portal.call(
				delete_usage_statistics, UsageEntity.USER, user_id
			)
			live_client.portal.call(delete_user, user_id)
		live_client.cookies.clear()
