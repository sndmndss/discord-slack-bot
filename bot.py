import argparse
import asyncio

from interfaces.discord_interface import run_discord_bot
from interfaces.slack_interface import run_slack_bot


async def main(one_way: bool):
    if one_way:
        await run_discord_bot()
    else:
        await asyncio.gather(run_discord_bot(), run_slack_bot())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--one-way", action="store_true", help="Enable only run_discord_bot"
    )
    args = parser.parse_args()
    asyncio.run(main(args.one_way))

