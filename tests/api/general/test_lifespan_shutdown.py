"""Verify orderly cleanup when the server lifespan ends."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def services(monkeypatch: pytest.MonkeyPatch):
	"""Replace service lifecycles without starting live clients."""
	from api import server

	maintenance = SimpleNamespace(start=Mock(), stop=AsyncMock())
	security = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
	start = AsyncMock()
	stop = AsyncMock()
	log = Mock()
	order = Mock()
	order.attach_mock(maintenance.stop, 'maintenance')
	order.attach_mock(security.stop, 'security')
	order.attach_mock(stop, 'api')
	monkeypatch.setattr(
		server, 'MaintenanceManager', lambda: maintenance
	)
	monkeypatch.setattr(server, 'SecurityManager', lambda: security)
	monkeypatch.setattr(server, 'start_api_lifecycle', start)
	monkeypatch.setattr(server, 'stop_api_lifecycle', stop)
	monkeypatch.setattr(server, 'rich_print', log)
	return SimpleNamespace(
		server=server,
		maintenance=maintenance,
		security=security,
		start=start,
		stop=stop,
		log=log,
		order=order,
	)


async def test_shutdown_stops_services_in_order(services) -> None:
	"""End the lifespan, then log successful service cleanup."""
	async with services.server.lifespan(services.server.app):
		services.start.assert_awaited_once()
		services.stop.assert_not_awaited()
	assert [call[0] for call in services.order.mock_calls] == [
		'maintenance',
		'security',
		'api',
	]
	messages = [call.args[0] for call in services.log.call_args_list]
	assert messages == [
		'Server termination detected. Shutting down services...',
		'Server shutdown complete.',
	]


@pytest.mark.parametrize('phase', ['startup', 'running'])
async def test_cancellation_still_stops_services(
	services,
	phase: str,
) -> None:
	"""Clean up interrupted startup and a cancelled lifespan."""
	if phase == 'startup':
		services.start.side_effect = asyncio.CancelledError()
	with pytest.raises(asyncio.CancelledError):
		async with services.server.lifespan(services.server.app):
			raise asyncio.CancelledError()
	services.maintenance.stop.assert_awaited_once()
	services.security.stop.assert_awaited_once()
	services.stop.assert_awaited_once()


@pytest.mark.parametrize('service', ['maintenance', 'security'])
async def test_stop_failure_does_not_skip_remaining_cleanup(
	services,
	service: str,
) -> None:
	"""Attempt remaining shutdown stages if one stage fails."""
	getattr(services, service).stop.side_effect = RuntimeError(
		'failed'
	)
	with pytest.raises(RuntimeError, match='failed'):
		async with services.server.lifespan(services.server.app):
			pass
	services.maintenance.stop.assert_awaited_once()
	services.security.stop.assert_awaited_once()
	services.stop.assert_awaited_once()
	assert not any(
		call.args[0] == 'Server shutdown complete.'
		for call in services.log.call_args_list
	)
