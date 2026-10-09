"""Load and validate the portfolio agent server environment."""

from os import getenv
from pathlib import Path

# --- Constants ---

_is_env_loaded: bool = False
_repo_root = Path(__file__).resolve().parents[2]
_env_to_env_file: dict[str, str] = {
	'testing': '.env.testing',
	'development': '.env.development',
	'production': '.env.production',
}

# --- Load Environment Variables ---


def load_environment_variables() -> None:
	"""Load and validate the selected server environment."""
	from dotenv import load_dotenv

	global _is_env_loaded
	if _is_env_loaded:
		return

	env = getenv('PORTFOLIO_AGENT_ENV')
	if env not in _env_to_env_file:
		raise RuntimeError(
			f'Invalid PORTFOLIO_AGENT_ENV: {env}. '
			f'Must be one of: {", ".join(_env_to_env_file)}.'
		)

	load_dotenv(
		dotenv_path=_repo_root / _env_to_env_file[env],
		override=env != 'production',
	)
	_check_environment()
	_is_env_loaded = True


# --- Environment Checks ---


def _check_environment_variable_str(name: str) -> None:
	"""Require a non-empty string environment variable."""
	value = getenv(name)
	if not value or not value.strip():
		raise RuntimeError(
			f"Environment variable '{name}' must not be empty."
		)


def _check_environment_variable_int(name: str) -> None:
	"""Require an integer port in the valid TCP port range."""
	value = getenv(name)
	try:
		port = int(value) if value is not None else None
	except ValueError as exc:
		raise RuntimeError(
			f"Environment variable '{name}' "
			'must be an integer port.'
		) from exc
	if port is None or not 1 <= port <= 65535:
		raise RuntimeError(
			f"Environment variable '{name}' "
			'must be a valid port.'
		)


def _check_environment() -> None:
	"""Validate the settings needed to start the server."""
	_check_environment_variable_str('PORTFOLIO_AGENT_ENV')
	_check_environment_variable_int('PORTFOLIO_AGENT_PORT')
	_check_environment_variable_str('CORS_ORIGINS')
	_check_environment_variable_str('COOKIE_DOMAIN')
	_check_environment_variable_str('JWT_SECRET')
	_check_environment_variable_str('MONGODB_URI')
	_check_environment_variable_str('OPENAI_KEY')
