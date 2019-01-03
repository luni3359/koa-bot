import os
import re
import tweepy
import discord
import asyncio
from discord.ext import commands
from discord.ext.commands import Bot

# Tweepy
# tweepy_auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

PROJECTPATH = os.path.dirname(__file__)
TOKENPATH = os.path.join(PROJECTPATH, "koa.token")
TOKEN = open(TOKENPATH, 'r').readline().strip()

client = discord.Client()


@client.event
async def on_ready():
    print("ready!")


@client.event
async def on_message(message):
    if message.channel.name != "koa-bot" or message.author == client.user:
        # print("This is me!")
        return

    urls = get_urls(message.content)
    if len(urls) > 0:
        domains = get_domains(urls)
        for i in range(len(domains)):
            domain = domains[i]
            if "twitter" in domain:
                await get_twitter_gallery(message, urls[i])


async def get_twitter_gallery(message, url):
    channel = message.channel

    # checking whether or not it contains an id
    id = url.split("/status/")
    if len(id) == 2:
        id = id[1].split('?')[0]
        question = await channel.send("Contains twitter image. Tweet ID is " + id + ". Would you like to see this gallery as a whole?")
        await question.add_reaction('\U00002b55')  # :o:
        await question.add_reaction('\U0000274c')  # :x:

        def check(reaction, user):
            return user == message.author and (str(reaction.emoji) == '\U00002b55' or str(reaction.emoji) == '\U0000274c') and reaction.message.id == question.id

        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await channel.send("D-don't ignore me!")
        else:
            user_reaction_response = str(reaction.emoji)

            # if user accepts
            if user_reaction_response == '\U00002b55':
                await channel.send("Good, now pretend I'm helping you!")
            # if user rejects
            else:
                await channel.send("Okay, not doing it")


def get_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", string)
    return url


def get_domains(array):
    domains = []

    for url in array:
        # thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
        domain = url.split("//")[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


client.run(TOKEN)
