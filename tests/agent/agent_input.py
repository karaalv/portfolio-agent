"""
Run an interactive agent session with live streaming output.
"""

import argparse
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from os import getenv
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from openai.types.responses import ResponseStreamEvent

from agent import main as agent_main
from api.lifecycle.environment import load_environment_variables
from database.mongodb.config import (
	is_mongo_connected,
	start_mongo_client,
	stop_mongo_client,
)
from openai_client.config import (
	start_openai_client,
	stop_openai_client,
)
from users.creation import create_user
from users.retrieval import does_user_exist


async def main(
	verbosity_level: int = 1,
	user_id: str | None = None,
) -> None:
	"""Start clients and interact until exit or cancellation.

	Create a new anonymous visitor unless an existing ID is
	supplied. Retain conversation records for later inspection.
	Close both clients even if startup or agent execution fails.
	"""
	environment = getenv('PORTFOLIO_AGENT_ENV')
	path = Path(__file__).resolve().parents[2]
	if environment not in {
		'testing',
		'development',
		'production',
	}:
		raise RuntimeError('Set PORTFOLIO_AGENT_ENV first.')
	if not (path / f'.env.{environment}').is_file():
		raise RuntimeError(f'Missing .env.{environment} file.')
	load_environment_variables()
	try:
		await start_mongo_client()
		if not await is_mongo_connected():
			raise RuntimeError(
				'MongoDB connection check failed.'
			)
		start_openai_client()
		if user_id is None:
			user_id = (await create_user()).user_id
		elif not await does_user_exist(user_id):
			raise ValueError(
				'The supplied user ID does not exist.'
			)
		print(f'Visitor ID: {user_id}')
		print('Enter exit or quit to finish. Ctrl-D also exits.')
		original = agent_main.stream_agent_response

		async def display(
			**kwargs,
		) -> AsyncIterator[ResponseStreamEvent]:
			"""
			Print real SDK text deltas and forward every event.
			"""
			async with aclosing(original(**kwargs)) as events:
				async for event in events:
					if (
						event.type
						== 'response.output_text.delta'
					):
						print(event.delta, end='', flush=True)
					elif event.type in {
						'error',
						'response.failed',
						'response.incomplete',
					}:
						raise RuntimeError(
							f'Agent stream failed: {event.type}'
						)
					yield event

		# Observe SDK events until publishing is ready.
		with patch.object(
			agent_main, 'stream_agent_response', display
		):
			while True:
				try:
					message = await asyncio.to_thread(
						input, '\nYou: '
					)
				except EOFError:
					break
				if message.strip().casefold() in {
					'exit',
					'quit',
				}:
					break
				if not message.strip():
					continue
				started = perf_counter()
				print('Assistant: ', end='', flush=True)
				await agent_main.agent_chat(
					user_id=user_id,
					user_input=message,
					verbosity_level=verbosity_level,
				)
				print()
				if verbosity_level > 0:
					elapsed = perf_counter() - started
					print(f'Completed in {elapsed:.2f}s.')
	finally:
		try:
			await stop_openai_client()
		finally:
			await stop_mongo_client()


def _parse_arguments() -> argparse.Namespace:
	"""
	Parse terminal verbosity and an optional existing identity.
	"""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		'--verbosity',
		'-v',
		type=int,
		choices=(0, 1, 2),
		default=1,
		help='0: minimal; 1: history/tools; 2: SDK events.',
	)
	parser.add_argument(
		'--user-id',
		help='Continue an existing visitor conversation.',
	)
	return parser.parse_args()


if __name__ == '__main__':
	arguments = _parse_arguments()
	try:
		asyncio.run(main(arguments.verbosity, arguments.user_id))
	except KeyboardInterrupt:
		print('\nSession ended.')
