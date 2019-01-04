import re
import random
import tweepy
import discord
import asyncio
from configparser import ConfigParser
from discord.ext import commands
from discord.ext.commands import Bot

config = ConfigParser()
config.read("config.ini")

auth = tweepy.OAuthHandler(config.get(
    "twitter", "consumer"), config.get("twitter", "consumer_secret"))
auth.set_access_token(config.get("twitter", "token"),
                      config.get("twitter", "token_secret"))
twitter_api = tweepy.API(auth)

client = discord.Client()


@client.event
async def on_ready():
    print("ready!")


@client.event
async def on_message_delete(message):
    if message.author.bot:
        return

    channel = message.channel

    deleted_quotes = [
        "{} said something. Nobody was there to listen...".format(
            message.author.mention),
        "I faintly heard {} whisper something. I wonder what they said...?".format(
            message.author.mention),
        "Is that you... {}? I think you need to be heard...".format(
            message.author.mention),
        "Mistakes always happen, but remember that not letting it out is dangerous, {}.".format(
            message.author.mention)
    ]

    await channel.send(random.choice(deleted_quotes))


@client.event
async def on_message(message):
    if message.author.bot:
        return

    urls = get_urls(message.content)
    if len(urls) > 0:
        domains = get_domains(urls)
        for i in range(len(domains)):
            domain = domains[i]
            if "twitter" in domain:
                await get_twitter_gallery(message, urls[i])

    if message.channel.name != "koa-bot":
        return


async def get_twitter_gallery(message, url):
    channel = message.channel

    # checking whether or not it contains an id
    id = url.split("/status/")
    if len(id) == 2:
        id = id[1].split('?')[0]
        question = await channel.send("Contains twitter image. Tweet ID is {}.\nWould you like to see this image gallery as a whole?".format(id))
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
                search = twitter_api.statuses_lookup([id])
                gallery_pics = []
                for tweet in search:
                    if not hasattr(tweet, "extended_entities") or len(tweet.extended_entities["media"]) <= 1:
                        print("Preview gallery not applicable.")
                        await channel.send("S-sorry, this tweet isn't really a gallery...")
                        continue

                    for content in tweet.extended_entities["media"][1:]:
                        gallery_pics.append(
                            content["media_url_https"] + ":orig")

                if len(gallery_pics) > 0:
                    await channel.send('\n'.join(gallery_pics))
            # if user rejects
            else:
                await channel.send("Okay, not doing it")

        await question.clear_reactions()


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


client.run(config.get("discord", "token"))
