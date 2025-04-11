import aiohttp

from settings.config import SLACK_CHAT_ID, DISCORD_WEBHOOK_URL

import discord

async def slack_send_message_as(
    client,
    text: str,
    username: str,
    discord_attachments: list[discord.Attachment],
    avatar_url: str | None = None,
) -> None:
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
        await client.chat_postMessage(
            channel=SLACK_CHAT_ID,
            text=text if text else "",
            username=username,
            icon_url=avatar_url,
            attachments=slack_attachments
        )
    except Exception as e:
        print(f"Unexpected error: {e}")

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
