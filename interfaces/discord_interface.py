import logging
import re

import discord

from interfaces.slack_interface import client as slack_client
from models.mapping import get_mapping, save_mapping
from settings.config import DISCORD_API_KEY, DISCORD_CHAT_ID
from utils import slack_send_message_as

client = discord.Client(intents=discord.Intents.all())


MENTION_RE = re.compile(r"<@!?(\d+)>")
CHANNEL_RE = re.compile(r"<#(\d+)>")
EMOJI_RE = re.compile(r"<a?:\w+:\d+>")
ROLE_RE = re.compile(r"<@&(\d+)>")


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

    return "\n".join(" ".join(line.split()) for line in content.splitlines())


@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Determine if the message is in the configured channel or a thread under it
    parent_id = getattr(message.channel, "parent_id", None)
    is_from_configured_channel = message.channel.id == int(DISCORD_CHAT_ID)
    is_from_thread_under_channel = parent_id == int(DISCORD_CHAT_ID)
    if not (is_from_configured_channel or is_from_thread_under_channel):
        return

    # If this is a Forum thread, only forward after a :ticket: reaction by Staff/Mods created a mapping
    is_forum_thread = False
    try:
        if isinstance(message.channel, discord.Thread):
            par = message.channel.parent
            if par and getattr(par, "type", None) == discord.ChannelType.forum:
                is_forum_thread = True
    except Exception:
        logging.exception("Failed checking forum thread status")

    author_name = message.author.display_name
    avatar_url = None  # you may switch to avatar.url if needed

    # Decide the source identifiers for persistence and threading
    is_in_thread = parent_id is not None
    discord_channel_id = str(parent_id if is_in_thread else message.channel.id)
    discord_source_id = str(message.channel.id if is_in_thread else message.id)

    # Find existing mapping to know if we should post in a Slack thread
    mapping = get_mapping(discord_channel_id, discord_source_id)

    # Gate: if it's a forum thread and no mapping (approval) yet, skip forwarding
    if is_forum_thread and mapping is None:
        logging.info("Skipping forum thread message without :ticket: approval (no mapping present). thread_id=%s msg_id=%s", message.channel.id, message.id)
        return

    text = await normalise_content(message)
    attachments = message.attachments

    # Prefix forum channel name in bold if this message is from a Forum post/thread
    try:
        is_forum = False
        channel = message.channel
        # If it's a thread, check its parent type; else check channel type directly
        if isinstance(channel, discord.Thread):
            parent = channel.parent
            if parent and getattr(parent, "type", None) == discord.ChannelType.forum:
                is_forum = True
                forum_name = parent.name
        else:
            if getattr(channel, "type", None) == discord.ChannelType.forum:
                is_forum = True
        if is_forum:
            prefix = f"*{message.channel.name}*\n"
            text = f"{prefix}{text}" if text else prefix
            logging.debug(
                "Forum message detected; prefixed with forum name: %s", forum_name
            )
    except Exception:
        logging.exception("Failed to determine forum status for message")

    try:
        if mapping:
            # Post as a reply in the existing Slack thread
            await slack_send_message_as(
                slack_client,
                text,
                author_name,
                attachments,
                avatar_url,
                thread_ts=mapping.slack_thread_ts,
                channel_id=mapping.slack_channel_id,
            )
        else:
            # Post a new root message (either channel message or the first message of a Discord thread)
            await slack_send_message_as(
                slack_client,
                text,
                author_name,
                attachments,
                avatar_url,
            )
    except Exception:
        logging.exception("Error forwarding message to Slack")


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    try:
        # Only care about :ticket: emoji (unicode)
        emoji_name = getattr(payload.emoji, 'name', None)
        if emoji_name != '🎫':
            return

        # Resolve guild (ignore DMs)
        guild = client.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            logging.debug("Raw reaction add without guild or guild not found: guild_id=%s", payload.guild_id)
            return

        # Resolve member: prefer payload.member; else get/fetch
        member = getattr(payload, 'member', None)
        if member is None:
            member = guild.get_member(payload.user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(payload.user_id)
                except Exception:
                    logging.exception("Failed to fetch member: user_id=%s", payload.user_id)
                    return
        # Ignore bot reactions
        if member.bot:
            return

        # Check roles Staff or Mods
        role_names = {r.name for r in getattr(member, 'roles', [])}
        if 'Staff' not in role_names and 'Mods' not in role_names:
            logging.debug("Ignoring :ticket: from non-privileged member: roles=%s", role_names)
            return

        # Robust channel resolution: channel may be a Thread or uncached
        channel = client.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(payload.channel_id)
            except Exception:
                logging.exception("Failed to fetch channel: channel_id=%s", payload.channel_id)
                return
        if channel is None:
            logging.warning("Channel still None after fetch: channel_id=%s", payload.channel_id)
            return

        # Trigger only for Forum contexts (forum channel or thread under forum)
        is_forum_context = False
        if isinstance(channel, discord.Thread):
            parent = channel.parent
            if parent and getattr(parent, 'type', None) == discord.ChannelType.forum:
                is_forum_context = True
        elif getattr(channel, 'type', None) == discord.ChannelType.forum:
            is_forum_context = True
        if not is_forum_context:
            logging.debug("Ignoring :ticket: reaction outside forum context")
            return

        # Fetch the message that received the reaction
        try:
            msg = await channel.fetch_message(payload.message_id)
        except Exception:
            logging.exception("Failed to fetch reacted message: message_id=%s", payload.message_id)
            return
        if msg is None:
            return

        # Construct ids for mapping: for threads map parent channel id with thread id; for channel map channel id with message id
        parent_id = getattr(msg.channel, 'parent_id', None)
        is_in_thread = parent_id is not None
        discord_channel_id = str(parent_id if is_in_thread else msg.channel.id)
        discord_source_id = str(msg.channel.id if is_in_thread else msg.id)

        # If mapping already exists, do nothing
        if get_mapping(discord_channel_id, discord_source_id):
            return

        # Prepare text with forum prefix
        text = await normalise_content(msg)
        try:
            forum_name = None
            ch = msg.channel
            if isinstance(ch, discord.Thread):
                p = ch.parent
                if p and getattr(p, 'type', None) == discord.ChannelType.forum:
                    forum_name = p.name
            elif getattr(ch, 'type', None) == discord.ChannelType.forum:
                forum_name = ch.name
            if forum_name:
                prefix = f"*{forum_name}*\n"
                text = f"{prefix}{text}" if text else prefix
        except Exception:
            logging.exception('Failed while building forum prefix on reaction')

        author_name = msg.author.display_name
        avatar_url = None

        # Post initial message to Slack and save mapping
        resp = await slack_send_message_as(
            slack_client,
            text,
            author_name,
            list(msg.attachments),
            avatar_url,
        )
        if resp is not None:
            save_mapping(
                discord_channel_id=discord_channel_id,
                discord_source_id=discord_source_id,
                slack_channel_id=str(resp['channel']),
                slack_thread_ts=str(resp['ts']),
            )
            logging.info('Approved forum thread via :ticket: by %s; mapping created for source=%s/%s', member.display_name, discord_channel_id, discord_source_id)
    except Exception:
        logging.exception('Error handling :ticket: reaction')


async def run_discord_bot():
    await client.start(token=DISCORD_API_KEY)
