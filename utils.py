import aiohttp
import logging

from settings.config import SLACK_CHAT_ID, DISCORD_WEBHOOK_URL

import discord

async def slack_send_message_as(
    client,
    text: str,
    username: str,
    discord_attachments: list[discord.Attachment],
    avatar_url: str | None = None,
    *,
    thread_ts: str | None = None,
    channel_id: str | None = None,
) -> dict | None:
    """Send a message to Slack.

    Args:
        client: Slack AsyncWebClient instance.
        text: Message text.
        username: Display name to use.
        discord_attachments: Discord attachments to convert for Slack.
        avatar_url: Optional avatar URL.
        thread_ts: If provided, post as a reply in this Slack thread.
        channel_id: Override the default SLACK_CHAT_ID.

    Returns:
        Slack API response dict with at least keys 'channel' and 'ts', or None on failure.
    """
    slack_attachments = []
    for att in discord_attachments:
        file_name_lower = att.filename.lower()
        if file_name_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            slack_attachments.append({
                "fallback": f"{att.filename} - {att.url}",
                "text": f"Image: {att.filename}",
                "image_url": att.url
            })
        else:
            slack_attachments.append({
                "fallback": f"{att.filename} - {att.url}",
                "text": f"File: {att.filename}\n<{att.url}|Download>",
            })

    try:
        target_channel = channel_id or SLACK_CHAT_ID
        if thread_ts:
            resp = await client.chat_postMessage(
                channel=target_channel,
                text=text if text else "",
                username=username,
                icon_url=avatar_url,
                attachments=slack_attachments,
                thread_ts=thread_ts,
            )
        else:
            resp = await client.chat_postMessage(
                channel=target_channel,
                text=text if text else "",
                username=username,
                icon_url=avatar_url,
                attachments=slack_attachments,
            )
        return {"channel": resp["channel"], "ts": resp["ts"]}
    except Exception:
        logging.exception("Unexpected error sending message to Slack")
        return None

async def discord_send_message_as(message: str, username: str, avatar_url: str | None = None) -> None:
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            DISCORD_WEBHOOK_URL,
            session=session
        )
        await webhook.send(
            content=message,
            username=username,
            avatar_url=avatar_url
        )
