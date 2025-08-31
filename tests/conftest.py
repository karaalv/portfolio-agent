"""
Pytest configuration
"""

import os

import pytest
from dotenv import load_dotenv

from common.utils import TerminalColors
from tests.config.server_config import (
	start_server,
	stop_server,
)

# Load test environment variables
load_dotenv(override=True, dotenv_path=os.path.abspath('.env.test'))


def pytest_configure():
	"""
	Configure pytest, start server
	and check environment.
	"""
	print(
		f'{TerminalColors.yellow}'
		f'Starting portfolio-agent tests...\n'
		f'{TerminalColors.reset}'
	)

	env = os.getenv('ENVIRONMENT')
	if env != 'test':
		pytest.exit(
			f'{TerminalColors.red}'
			f"Environment is not set to 'test'. "
			f'Current environment: {env}.'
			f'{TerminalColors.reset}'
		)

	# Start the server before running tests
	start_server()


def pytest_sessionfinish():
	"""
	Teardown after all tests are done.
	Closes the MongoDB connection.
	"""
	# Stop the server after tests
	stop_server()

	print(
		f'{TerminalColors.yellow}\nTest runtime finished.{TerminalColors.reset}'
	)
