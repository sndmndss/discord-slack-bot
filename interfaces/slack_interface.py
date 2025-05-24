import re
import asyncio
from typing import Dict

from settings.config import SLACK_SOCKET_KEY, SLACK_BOT_KEY
from utils import discord_send_message_as

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient

USER_MENTION_RE = re.compile(r"<@([UW][A-Z0-9]+)(?:\|[^>]*)?>")
CHANNEL_MENTION_RE = re.compile(r"<#(C[A-Z0-9]+)(?:\|[^>]*)?>")
USERGROUP_MENTION_RE = re.compile(r"<!subteam\^([A-Z0-9]+)(?:\|[^>]*)?>")
SPECIAL_MENTION_RE = re.compile(r"<!(channel|here|everyone)>")
EMOJI_RE = re.compile(r":([+\w-]+):")

async def normalise_slack_content(text: str, client: AsyncWebClient) -> str:
    user_ids = set(USER_MENTION_RE.findall(text))
    channel_ids = set(CHANNEL_MENTION_RE.findall(text))
    usergroup_ids = set(USERGROUP_MENTION_RE.findall(text))

    async def fetch_user(uid: str):
        try:
            info = await client.users_info(user=uid)
            profile = info["user"]["profile"]
            name = profile.get("display_name") or profile.get("real_name") or info["user"]["name"]
            return uid, name
        except Exception:
            return uid, "unknown"

    user_name_map: Dict[str, str] = dict(await asyncio.gather(*(fetch_user(uid) for uid in user_ids)))

    async def fetch_channel(cid: str):
        try:
            info = await client.conversations_info(channel=cid)
            return cid, info["channel"]["name"]
        except Exception:
            return cid, "unknown-channel"

    channel_name_map: Dict[str, str] = dict(await asyncio.gather(*(fetch_channel(cid) for cid in channel_ids)))

    usergroup_name_map: Dict[str, str] = {}
    if usergroup_ids:
        try:
            groups = await client.usergroups_list()
            handle_lookup = {g["id"]: g["handle"] for g in groups["usergroups"]}
            usergroup_name_map = {gid: handle_lookup.get(gid, "group") for gid in usergroup_ids}
        except Exception:
            usergroup_name_map = {gid: "group" for gid in usergroup_ids}

    try:
        emoji_resp = await client.emoji_list()
        custom_emojis = set(emoji_resp["emoji"].keys())
    except Exception:
        custom_emojis = set()

    text = USER_MENTION_RE.sub(lambda m: f"@{user_name_map.get(m.group(1), 'unknown')}", text)
    text = CHANNEL_MENTION_RE.sub(lambda m: f"#{channel_name_map.get(m.group(1), 'unknown-channel')}", text)
    text = USERGROUP_MENTION_RE.sub(lambda m: f"@{usergroup_name_map.get(m.group(1), 'group')}", text)
    text = SPECIAL_MENTION_RE.sub(lambda m: f"@{m.group(1)}", text)

    def emoji_repl(match):
        name = match.group(1)
        return "" if name in custom_emojis else match.group(0)

    text = EMOJI_RE.sub(emoji_repl, text)

    return "\n".join(" ".join(line.split()) for line in text.splitlines())

app = AsyncApp(token=SLACK_BOT_KEY)
client = AsyncWebClient(token=SLACK_BOT_KEY)

@app.event("message")
async def handle_message_events(body, say, client: AsyncWebClient):
    event = body.get("event", {})
    user_id = event.get("user")
    text = event.get("text", "") or ""
    if "joined the channel" in text or "left the channel" in text:
        return
    if not user_id:
        return
    try:
        user_info = await client.users_info(user=user_id)
        user_data = user_info["user"]
        displayname = user_data["profile"].get("display_name") or user_data["profile"].get("real_name") or user_data["name"]
        clean_text = await normalise_slack_content(text, client)
        await discord_send_message_as(clean_text, displayname, None)
    except Exception as e:
        print(f"Unexpected error: {e}")

async def run_slack_bot():
    handler = AsyncSocketModeHandler(app, SLACK_SOCKET_KEY)
    await handler.start_async()
