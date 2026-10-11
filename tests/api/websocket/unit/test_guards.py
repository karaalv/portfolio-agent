"""Check hard size limits before parsing and sanitisation."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import WebSocketException

from api.websocket.helpers import guards
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import (
	BlockedEntity,
	BlockedRecord,
)
from shared.time import get_utc_datetime_now


@pytest.fixture
def block(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Model the existing block helper's persistence and raise."""
	now = get_utc_datetime_now()
	record = BlockedRecord(
		entity=BlockedEntity.USER,
		entity_id='visitor',
		blocked_at=now,
		blocked_until=now + timedelta(days=1),
		reason='Oversized input',
	)
	mock = AsyncMock(side_effect=EntityBlockedException(record))
	monkeypatch.setattr(guards, 'apply_24h_block', mock)
	return mock


@pytest.fixture
def close_users(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
	"""Capture closure of every connection for the user."""
	mock = AsyncMock()
	monkeypatch.setattr(
		guards,
		'get_websocket_registry',
		lambda: SimpleNamespace(remove_user_connections=mock),
	)
	return mock


@pytest.mark.parametrize('content', ['a' * 16384, 'é' * 8192])
async def test_content_at_byte_limit_is_allowed(
	content: str,
	block: AsyncMock,
	close_users: AsyncMock,
) -> None:
	"""Allow exactly 16 KiB, measured in UTF-8 bytes."""
	await guards.guard_ws_content('visitor', content)
	block.assert_not_awaited()
	close_users.assert_not_awaited()


@pytest.mark.parametrize('content', ['a' * 16385, 'é' * 8193])
async def test_oversized_content_blocks_and_closes(
	content: str,
	block: AsyncMock,
	close_users: AsyncMock,
) -> None:
	"""Persist a user block and close all their sockets."""
	with pytest.raises(WebSocketException) as exc:
		await guards.guard_ws_content('visitor', content)
	assert exc.value.code == 1009
	block.assert_awaited_once_with(
		BlockedEntity.USER,
		'visitor',
		'WebSocket content size limit exceeded.',
	)
	close_users.assert_awaited_once_with(
		'visitor',
		reason='Input size limit exceeded.',
		close_code=1009,
	)


@pytest.mark.parametrize(
	'count, blocked', [(10000, False), (10001, True)]
)
async def test_original_token_limit(
	count: int,
	blocked: bool,
	block: AsyncMock,
	close_users: AsyncMock,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Count the original text and enforce a strict upper bound."""
	encode = Mock(return_value=[0] * count)
	monkeypatch.setattr(
		guards.tiktoken,
		'get_encoding',
		lambda _: SimpleNamespace(encode=encode),
	)
	if blocked:
		with pytest.raises(WebSocketException) as exc:
			await guards.guard_agent_input('visitor', 'original')
		assert exc.value.code == 1009
		block.assert_awaited_once_with(
			BlockedEntity.USER,
			'visitor',
			'Agent input token limit exceeded.',
		)
		close_users.assert_awaited_once()
	else:
		await guards.guard_agent_input('visitor', 'original')
		block.assert_not_awaited()
	encode.assert_called_once_with(
		'original', disallowed_special=()
	)


async def test_tokeniser_treats_special_markers_as_text(
	block: AsyncMock,
	close_users: AsyncMock,
) -> None:
	"""Use the real encoding without rejecting special strings."""
	await guards.guard_agent_input('visitor', '<|endoftext|>')
	block.assert_not_awaited()


async def test_persistence_failure_still_closes_connections(
	block: AsyncMock,
	close_users: AsyncMock,
) -> None:
	"""Close offending connections even if a block write fails."""
	block.side_effect = RuntimeError('Database unavailable')
	with pytest.raises(RuntimeError):
		await guards.guard_ws_content('visitor', 'a' * 16385)
	close_users.assert_awaited_once()
