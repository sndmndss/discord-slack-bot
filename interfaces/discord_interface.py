import discord

from interfaces.slack_interface import client as slack_client

from utils import slack_send_message_as

from settings.config import DISCORD_CHAT_ID, DISCORD_API_KEY



client = discord.Client(intents=discord.Intents.all())

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

        await slack_send_message_as(
            slack_client,
            text,
            author_name,
            attachments,
            avatar_url
        )

async def run_discord_bot():
    await client.start(token=DISCORD_API_KEY)

