# ruff: noqa: E402
"""
This module contains tests for
the agent using terminal input.
"""

import os

from dotenv import load_dotenv

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.test'))

import asyncio

from agent.main import chat
from common.utils import TerminalColors, Timer
from database.mongodb.config import (
	close_mongo,
	connect_mongo,
)
from users.main import create_user, does_user_exist

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'test_user_id.txt')


async def setup():
	try:
		with open(file_path) as f:
			id = f.read().strip()
	except FileNotFoundError:
		id = None

	if id and await does_user_exist(id):
		return id

	user = await create_user()
	with open(file_path, 'w') as f:
		f.write(str(user.user_id))

	return user.user_id


async def main():
	await connect_mongo()
	user_id = await setup()

	print('\nInteract with agent:\n')
	timer = Timer(start=False)

	while True:
		user_message = input('>> ')

		if user_message == 'exit':
			await close_mongo()
			break

		timer.start()
		agent_message = await chat(
			user_id=user_id,
			input=user_message,
			verbose=True,
			ip='127.0.0.1',
			ua='test_user_agent',
		)
		response_time = timer.stop()

		print(
			f'{TerminalColors.yellow}'
			f'Agent response in {response_time:.4f} seconds'
			f'{TerminalColors.reset}'
		)

		print(
			f'{TerminalColors.yellow}'
			f'Agent: '
			f'{TerminalColors.reset}'
			f'{agent_message}\n'
		)


if __name__ == '__main__':
	asyncio.run(main())
