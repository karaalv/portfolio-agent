"""Check required cookie domain configuration at startup."""

import pytest

from api.config.cookies import get_cookie_domain
from api.lifecycle.environment import _check_environment

pytestmark = pytest.mark.unit


@pytest.fixture
def valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Provide server settings without reading env files."""
	for name, value in {
		'PORTFOLIO_AGENT_ENV': 'testing',
		'PORTFOLIO_AGENT_PORT': '8000',
		'CORS_ORIGINS': 'https://example.com',
		'COOKIE_DOMAIN': 'example.com',
		'JWT_SECRET': 'test-secret',
		'MONGODB_URI': 'test-uri',
		'OPENAI_KEY': 'test-key',
	}.items():
		monkeypatch.setenv(name, value)


@pytest.mark.parametrize('domain', [None, '', '   '])
def test_missing_cookie_domain_prevents_startup(
	valid_environment: None,
	monkeypatch: pytest.MonkeyPatch,
	domain: str | None,
) -> None:
	"""Reject absent or blank domains before starting clients."""
	if domain is None:
		monkeypatch.delenv('COOKIE_DOMAIN')
	else:
		monkeypatch.setenv('COOKIE_DOMAIN', domain)
	with pytest.raises(RuntimeError, match='COOKIE_DOMAIN'):
		_check_environment()
	with pytest.raises(RuntimeError, match='COOKIE_DOMAIN'):
		get_cookie_domain()


def test_cookie_domain_loaded_from_environment(
	valid_environment: None,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Validate and read the trimmed domain on demand."""
	monkeypatch.setenv('COOKIE_DOMAIN', ' example.com ')
	_check_environment()
	assert get_cookie_domain() == 'example.com'
