"""Verify security service ordering and failure cleanup."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from api.security import security_manager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager_services():
	"""Replace services and record their lifecycle calls."""
	with (
		patch.object(security_manager, 'UsageObserver') as usage,
		patch.object(security_manager, 'BlockObserver') as block,
		patch.object(
			security_manager,
			'start_security_client',
			new_callable=AsyncMock,
		) as start_client,
		patch.object(
			security_manager,
			'stop_security_client',
			new_callable=AsyncMock,
		) as stop_client,
	):
		usage.return_value.stop = AsyncMock()
		block.return_value.stop = AsyncMock()
		calls = Mock()
		calls.attach_mock(start_client, 'start_client')
		calls.attach_mock(
			usage.return_value.start, 'start_usage'
		)
		calls.attach_mock(
			block.return_value.start, 'start_block'
		)
		calls.attach_mock(block.return_value.stop, 'stop_block')
		calls.attach_mock(usage.return_value.stop, 'stop_usage')
		calls.attach_mock(stop_client, 'stop_client')
		yield security_manager.SecurityManager(), calls


async def test_security_services_start_and_stop_in_order(
	manager_services,
) -> None:
	"""Keep the client available for both observer lifetimes."""
	manager, calls = manager_services
	assert calls.mock_calls == []
	await manager.start()
	await manager.stop()
	assert [call[0] for call in calls.mock_calls] == [
		'start_client',
		'start_usage',
		'start_block',
		'stop_block',
		'stop_usage',
		'stop_client',
	]
	manager.block_observer.stop.assert_awaited_once()
	manager.usage_observer.stop.assert_awaited_once()
	calls.stop_client.assert_awaited_once()


async def test_partial_startup_stops_security_services(
	manager_services,
) -> None:
	"""Undo startup when a later observer cannot start."""
	manager, calls = manager_services
	manager.block_observer.start.side_effect = RuntimeError(
		'Cannot start observer'
	)
	with pytest.raises(RuntimeError, match='Cannot start'):
		await manager.start()
	manager.block_observer.stop.assert_awaited_once()
	manager.usage_observer.stop.assert_awaited_once()
	calls.stop_client.assert_awaited_once()


async def test_shutdown_failure_still_stops_other_services(
	manager_services,
) -> None:
	"""A failed observer stop must not skip remaining cleanup."""
	manager, calls = manager_services
	manager.block_observer.stop.side_effect = RuntimeError(
		'Cannot stop observer'
	)
	with pytest.raises(RuntimeError, match='Cannot stop'):
		await manager.stop()
	manager.usage_observer.stop.assert_awaited_once()
	calls.stop_client.assert_awaited_once()
