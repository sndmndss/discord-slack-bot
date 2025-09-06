import os
from datetime import datetime
from typing import Optional

from peewee import (
    Model,
    CharField,
    DateTimeField,
    AutoField,
    CompositeKey,
)
from peewee import DatabaseProxy

try:
    # playhouse is bundled with peewee
    from playhouse.db_url import connect as db_connect
except Exception:  # pragma: no cover
    db_connect = None  # type: ignore


_database_proxy: DatabaseProxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = _database_proxy


class SlackDiscordMap(BaseModel):
    id = AutoField()
    # Discord parent channel id (for threads it's the parent text channel; for channel messages it's the same as message.channel.id)
    discord_channel_id = CharField()
    # Discord source id: thread id if message is inside a thread; otherwise the message id
    discord_source_id = CharField()

    # Slack identifiers where the message/thread was created
    slack_channel_id = CharField()
    slack_thread_ts = CharField()  # Slack thread root ts

    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "slack_discord_map"
        indexes = (
            # Ensure uniqueness for mapping within a given Discord channel
            (("discord_channel_id", "discord_source_id"), True),
        )


def init_database() -> None:
    """Initialize the Peewee database from DATABASE_URL or fallback to SQLite.

    Should be called once on app startup before any DB operations.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_connect is not None:
        try:
            db = db_connect(db_url)
            # Try connecting to validate driver availability; fallback on failure
            db.connect(reuse_if_open=True)
            db.close()
        except Exception:
            from peewee import SqliteDatabase

            db = SqliteDatabase("data.db")
    else:
        from peewee import SqliteDatabase

        db = SqliteDatabase("data.db")
    _database_proxy.initialize(db)


def create_tables() -> None:
    """Create required tables if they do not exist."""
    _database_proxy.create_tables([SlackDiscordMap])


def get_mapping(discord_channel_id: str, discord_source_id: str) -> Optional[SlackDiscordMap]:
    try:
        return (
            SlackDiscordMap.select()
            .where(
                (SlackDiscordMap.discord_channel_id == discord_channel_id)
                & (SlackDiscordMap.discord_source_id == discord_source_id)
            )
            .get()
        )
    except SlackDiscordMap.DoesNotExist:
        return None


def save_mapping(
    discord_channel_id: str,
    discord_source_id: str,
    slack_channel_id: str,
    slack_thread_ts: str,
) -> SlackDiscordMap:
    mapping = get_mapping(discord_channel_id, discord_source_id)
    if mapping is not None:
        return mapping
    return SlackDiscordMap.create(
        discord_channel_id=discord_channel_id,
        discord_source_id=discord_source_id,
        slack_channel_id=slack_channel_id,
        slack_thread_ts=slack_thread_ts,
    )
