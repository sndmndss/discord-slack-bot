import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(filename='.env'))

DISCORD_CHAT_ID = os.getenv("DISCORD_CHAT_ID")
SLACK_CHAT_ID = os.getenv("SLACK_CHAT_ID")
SLACK_SOCKET_KEY = os.getenv("SLACK_SOCKET_KEY")
SLACK_BOT_KEY = os.getenv("SLACK_BOT_KEY")
DISCORD_API_KEY = os.getenv("DISCORD_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

assert DISCORD_CHAT_ID is not None, "DISCORD_CHAT_ID is not set in the environment"
assert SLACK_CHAT_ID is not None, "SLACK_CHAT_ID is not set in the environment"
assert SLACK_SOCKET_KEY is not None, "SLACK_SOCKET_KEY is not set in the environment"
assert DISCORD_API_KEY is not None, "DISCORD_API_KEY is not set in the environment"
assert SLACK_BOT_KEY is not None, "SLACK_BOT_KEY is not set in the environment"
assert DISCORD_WEBHOOK_URL is not None, "DISCORD_WEBHOOK_URL is not set in the environment"

