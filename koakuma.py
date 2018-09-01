import os
import discord
import asyncio
from discord.ext import commands
from discord.ext.commands import Bot

PROJECTPATH = os.path.dirname(__file__)
TOKENPATH = os.path.join(PROJECTPATH, "koa.token")
TOKEN = open(TOKENPATH, "r").readline().strip()

client = discord.Client()


@client.event
async def on_ready():
    print("ready!")


@client.event
async def on_message(message):
    # <crow noises>
    # say = lambda s: client.send_message(message.channel, s)
    def say(s): return client.send_message(message.channel, s)

    if message.author == client.user or str(message.channel) != "koa-bot":
        return

    await say("Hi there, " + str(message.author.display_name) + "!")


client.run(TOKEN)
