import os
import re
import random
import tweepy
import discord
import asyncio
from configparser import ConfigParser
from discord.ext import commands
from discord.ext.commands import Bot

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))

config = ConfigParser()
config.read(os.path.join(SOURCE_DIR, "config.ini"))

auth = tweepy.OAuthHandler(config.get("twitter", "consumer"), config.get("twitter", "consumer_secret"))
auth.set_access_token(config.get("twitter", "token"), config.get("twitter", "token_secret"))
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
        "{} said something. Nobody was there to listen...".format(message.author.mention),
        "I faintly heard {} whisper something. I wonder what they said...?".format(message.author.mention),
        "Is that you... {}? I think you need to be heard...".format(message.author.mention),
        "Mistakes always happen, but remember that not letting it out is dangerous, {}.".format(message.author.mention)
    ]

    await channel.send(random.choice(deleted_quotes))


@client.event
async def on_message(message):
    # Prevent bot from spamming itself
    if message.author.bot:
        return

    # Test for image urls
    urls = get_urls(message.content)
    if len(urls) > 0 and len(message.embeds) > 0:
        domains = get_domains(urls)
        for i in range(len(domains)):
            domain = domains[i]
            if "twitter" in domain:
                await get_twitter_gallery(message, urls[i])

    # Features under testing, only allowed under this channel
    if message.channel.name != "koa-bot":
        # None, currently
        return


async def get_twitter_gallery(message, url):
    channel = message.channel

    # Checking whether or not it contains an id
    id = url.split("/status/")
    if len(id) == 2:
        id = id[1].split('?')[0]
        tweet = twitter_api.get_status(id, tweet_mode="extended")

        if not hasattr(tweet, "extended_entities") or len(tweet.extended_entities["media"]) <= 1:
            print("Preview gallery not applicable.")
            return

        gallery_pics = []
        for picture in tweet.extended_entities["media"][1:]:
            if picture["type"] != "photo":
                return

            gallery_pics.append(picture["media_url_https"] + ":orig")

        gallery_pics_total = len(gallery_pics)
        for picture in gallery_pics:
            gallery_pics_total -= 1

            embed = discord.Embed()
            embed.set_author(
                name="{} (@{})".format(tweet.author.name, tweet.author.screen_name),
                url="https://twitter.com/{}".format(tweet.author.screen_name),
                icon_url=tweet.author.profile_image_url_https
            )
            embed.set_image(url=picture)

            # If it's the last picture to show, add a brand footer
            if gallery_pics_total <= 0:
                embed.set_footer(
                    text="Twitter", icon_url="https://images-ext-1.discordapp.net/external/bXJWV2Y_F3XSra_kEqIYXAAsI3m1meckfLhYuWzxIfI/https/abs.twimg.com/icons/apple-touch-icon-192x192.png"
                )

            await channel.send(embed=embed)


def get_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", string)
    return url


def get_domains(array):
    domains = []

    for url in array:
        # thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
        domain = url.split("//")[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


client.run(config.get("discord", "token"))
