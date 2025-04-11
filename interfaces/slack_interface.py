from settings.config import SLACK_SOCKET_KEY, SLACK_BOT_KEY
from utils import discord_send_message_as

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient


app = AsyncApp(
    token=SLACK_BOT_KEY
)
client = AsyncWebClient(token=SLACK_BOT_KEY)


@app.event("message")
async def handle_message_events(body, say, client):
    event = body.get("event", {})
    user_id = event.get("user")
    text = event.get("text", "")
    if "joined the channel" in text or "left the channel" in text:
        return

    if not user_id:
        return

    try:
        user_info = await client.users_info(user=user_id)
        user_data = user_info["user"]
        display_name = user_data["profile"].get("display_name") or user_data["profile"].get("real_name",
                                                                                            user_data["name"])
        await discord_send_message_as(text, display_name, None)
        # avatar_url = user_data["profile"].get("image_512") or user_data["profile"].get("image_192")

    except Exception as e:
        print(f"Unexpected error: {e}")



async def run_slack_bot():
    handler = AsyncSocketModeHandler(app, SLACK_SOCKET_KEY)
    await handler.start_async()



