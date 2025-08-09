"""
This module contains tests for
the agent using terminal input.
"""
import os
from dotenv import load_dotenv

load_dotenv(
    override=True, 
    dotenv_path=os.path.abspath(".env.test")
)

import asyncio
from common.utils import TerminalColors
from database.mongodb.config import connect_mongo, close_mongo
from agent.main import chat

async def main():
    await connect_mongo()
    print("Interact with agent:")
    while True:
        user_message = input(">> ")

        if user_message == "exit":
            await close_mongo()
            break

        agent_message = await chat(
            user_id='test_user',
            input=user_message,
            verbose=True
        )

        print(
            f"{TerminalColors.yellow}"
            f"Agent: "
            f"{TerminalColors.reset}"
            f"{agent_message}\n"
        )

if __name__ == "__main__":
    asyncio.run(main())