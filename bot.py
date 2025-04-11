import asyncio
from interfaces.discord_interface import run_discord_bot
from interfaces.slack_interface import run_slack_bot


async def main():
    await asyncio.gather(run_discord_bot(), run_slack_bot())

if __name__ == "__main__":
    asyncio.run(main())
