"""Tests for server startup validation."""

from unittest.mock import patch

import pytest

from api.lifecycle import environment
from run import main


def test_main_requires_environment(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Reject startup when PORTFOLIO_AGENT_ENV is unset."""
	monkeypatch.delenv('PORTFOLIO_AGENT_ENV', raising=False)
	monkeypatch.setattr(environment, '_is_env_loaded', False)

	with patch('uvicorn.run') as start_server:
		with pytest.raises(
			RuntimeError, match='Invalid PORTFOLIO_AGENT_ENV'
		):
			main()

	start_server.assert_not_called()


def test_main_sets_websocket_transport_limit(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Pass the 64 KiB incoming message ceiling to Uvicorn."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'testing')
	monkeypatch.setenv('PORTFOLIO_AGENT_PORT', '8000')
	with (
		patch('run.load_environment_variables'),
		patch('uvicorn.run') as start_server,
	):
		main()
	assert start_server.call_args.kwargs['ws_max_size'] == 65536
