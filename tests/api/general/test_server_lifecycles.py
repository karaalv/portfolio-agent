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
