"""Block oversized requests before cleaning agent input."""

from typing import NoReturn

import tiktoken
from fastapi import WebSocketException

from api.config.websocket import (
	INPUT_TOKEN_ENCODING,
	MAX_CONTENT_SIZE_BYTES,
	MAX_INPUT_TOKENS,
)
from api.websocket import get_websocket_registry
from exceptions.security import EntityBlockedException
from schemas.security.monitoring.blocked import BlockedEntity
from security.monitoring.blocked.enforcement import (
	apply_24h_block,
)


async def guard_ws_content(user_id: str, content: str) -> None:
	"""Check the entire UTF-8 envelope before JSON parsing."""
	if len(content.encode('utf-8')) > MAX_CONTENT_SIZE_BYTES:
		await _block_oversized_input(
			user_id, 'WebSocket content size limit exceeded.'
		)


async def guard_agent_input(user_id: str, payload: str) -> None:
	"""Check original payload tokens before text sanitisation."""
	encoding = tiktoken.get_encoding(INPUT_TOKEN_ENCODING)
	count = len(encoding.encode(payload, disallowed_special=()))
	if count > MAX_INPUT_TOKENS:
		await _block_oversized_input(
			user_id, 'Agent input token limit exceeded.'
		)


async def _block_oversized_input(
	user_id: str, reason: str
) -> NoReturn:
	"""Persist a user block and close all their local sockets."""
	try:
		await apply_24h_block(
			BlockedEntity.USER, user_id, reason
		)
	except EntityBlockedException as exc:
		raise WebSocketException(
			code=1009, reason='Input size limit exceeded.'
		) from exc
	finally:
		await get_websocket_registry().remove_user_connections(
			user_id,
			reason='Input size limit exceeded.',
			close_code=1009,
		)
