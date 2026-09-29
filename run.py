"""Load server settings and start the Portfolio Agent API."""

from os import getenv

from api.lifecycle.environment import load_environment_variables
from shared.logging import LogStyle, rich_print


def main() -> None:
	"""Validate the environment and launch the API server."""
	import uvicorn

	load_environment_variables()
	env = getenv('PORTFOLIO_AGENT_ENV', '')
	port = int(getenv('PORTFOLIO_AGENT_PORT', ''))
	rich_print(
		message=(
			f'Starting Portfolio Agent server on port '
			f'{port} in {env} environment...'
		),
		style=LogStyle.INFO,
		prefix='api.server',
	)

	uvicorn.run(
		app='api.server:app',
		host='0.0.0.0',
		port=port,
		log_level='info' if env == 'production' else 'debug',
		workers=1,
		reload=env == 'development',
	)


if __name__ == '__main__':
	main()
