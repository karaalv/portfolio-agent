"""Tests for server startup validation."""

from os import getenv
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


@pytest.mark.parametrize(
	('name', 'overrides'),
	[
		('testing', True),
		('development', True),
		('staging', False),
		('production', False),
	],
)
def test_environment_file_loading(
	monkeypatch: pytest.MonkeyPatch, tmp_path, name, overrides
) -> None:
	"""Load the selected file with deployment variable precedence."""
	settings = {
		'PORTFOLIO_AGENT_PORT': '8100',
		'CORS_ORIGINS': 'https://example.com',
		'COOKIE_DOMAIN': 'example.com',
		'JWT_SECRET': 'test-secret',
		'MONGODB_URI': 'mongodb://localhost/test',
		'OPENAI_KEY': 'test-key',
	}
	for key in settings:
		monkeypatch.delenv(key, raising=False)
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', name)
	monkeypatch.setenv('PORTFOLIO_AGENT_PORT', '8200')
	monkeypatch.setattr(environment, '_repo_root', tmp_path)
	monkeypatch.setattr(environment, '_is_env_loaded', False)
	(tmp_path / f'.env.{name}').write_text(
		'\n'.join(f'{key}={value}' for key, value in settings.items())
	)

	environment.load_environment_variables()

	assert getenv('PORTFOLIO_AGENT_PORT') == (
		'8100' if overrides else '8200'
	)
	assert getenv('OPENAI_KEY') == 'test-key'
	assert environment._is_env_loaded


@pytest.mark.parametrize('name', ['staging', 'production'])
def test_deployment_environment_without_file(
	monkeypatch: pytest.MonkeyPatch, tmp_path, name
) -> None:
	"""Accept fully injected settings without a local dotenv file."""
	monkeypatch.setattr(environment, '_repo_root', tmp_path)
	monkeypatch.setattr(environment, '_is_env_loaded', False)
	for key, value in {
		'PORTFOLIO_AGENT_ENV': name,
		'PORTFOLIO_AGENT_PORT': '8000',
		'CORS_ORIGINS': 'https://example.com',
		'COOKIE_DOMAIN': 'example.com',
		'JWT_SECRET': 'test-secret',
		'MONGODB_URI': 'mongodb://localhost/test',
		'OPENAI_KEY': 'test-key',
	}.items():
		monkeypatch.setenv(key, value)

	environment.load_environment_variables()

	assert environment._is_env_loaded


@pytest.mark.parametrize('port', ['invalid', '0', '65536'])
def test_staging_rejects_invalid_port(
	monkeypatch: pytest.MonkeyPatch, tmp_path, port
) -> None:
	"""Reject invalid staging ports before completing the load."""
	monkeypatch.setenv('PORTFOLIO_AGENT_ENV', 'staging')
	monkeypatch.setenv('PORTFOLIO_AGENT_PORT', port)
	monkeypatch.setattr(environment, '_repo_root', tmp_path)
	monkeypatch.setattr(environment, '_is_env_loaded', False)
	with pytest.raises(RuntimeError, match='PORTFOLIO_AGENT_PORT'):
		environment.load_environment_variables()
	assert not environment._is_env_loaded
