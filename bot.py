import argparse
import asyncio
import logging
import sys


async def main(one_way: bool):
    # Local imports after logging is configured to ensure any import-time errors are logged
    from models.mapping import init_database, create_tables
    from interfaces.discord_interface import run_discord_bot
    from interfaces.slack_interface import run_slack_bot

    # Initialize database and ensure tables exist before starting bots
    init_database()
    create_tables()

    if one_way:
        logging.info("Starting Discord bot (one-way mode)...")
        await run_discord_bot()
    else:
        logging.info("Starting Discord and Slack bots...")
        await asyncio.gather(run_discord_bot(), run_slack_bot())


if __name__ == "__main__":
    # Configure root logger to output to stdout with detailed format
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--one-way", action="store_true", help="Enable only run_discord_bot"
    )
    args = parser.parse_args()
    try:
        asyncio.run(main(args.one_way))
    except Exception:
        logging.exception("Fatal error running bots")
        raise

