import discord
import re

from interfaces.slack_interface import client as slack_client

from utils import slack_send_message_as

from settings.config import DISCORD_CHAT_ID, DISCORD_API_KEY



client = discord.Client(intents=discord.Intents.all())


MENTION_RE = re.compile(r"<@!?(\d+)>")
CHANNEL_RE = re.compile(r"<#(\d+)>")
EMOJI_RE   = re.compile(r"<a?:\w+:\d+>")
ROLE_RE    = re.compile(r"<@&(\d+)>")

async def normalise_content(message: discord.Message) -> str:
    """Return message.content with Discord-specific markup replaced/removed."""
    guild = message.guild
    content = message.content

    def role_repl(match: re.Match) -> str:
        rid = int(match.group(1))
        role = guild.get_role(rid)
        return f"@{role.name}" if role else "@unknown-role"

    content = ROLE_RE.sub(role_repl, content)

    def user_repl(match: re.Match) -> str:
        uid = int(match.group(1))
        member = guild.get_member(uid)
        return f"@{member.display_name}" if member else "@unknown"

    content = MENTION_RE.sub(user_repl, content)

    def channel_repl(match: re.Match) -> str:
        cid = int(match.group(1))
        channel = guild.get_channel(cid)
        return f"#{channel.name}" if channel else "#unknown-channel"

    content = CHANNEL_RE.sub(channel_repl, content)

    content = EMOJI_RE.sub("", content)

    return " ".join(content.split())


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return


    if message.channel.id == int(DISCORD_CHAT_ID):
        author_name = message.author.display_name
        # avatar_url = message.author.avatar.url

        avatar_url = None
        text = message.content
        attachments = message.attachments
        text = await normalise_content(message)
        await slack_send_message_as(
            slack_client,
            text,
            author_name,
            attachments,
            avatar_url
        )

async def run_discord_bot():
    await client.start(token=DISCORD_API_KEY)

