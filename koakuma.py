import os
import re
import random
import tweepy
import discord
import asyncio
import datetime
import subprocess
import commentjson
import gaka as art
import urusai as channel_activity
from discord.ext import commands

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(SOURCE_DIR, "config.jsonc")) as json_file:
    data = commentjson.load(json_file)

auth = tweepy.OAuthHandler(data["keys"]["twitter"]["consumer"], data["keys"]["twitter"]["consumer_secret"])
auth.set_access_token(data["keys"]["twitter"]["token"], data["keys"]["twitter"]["token_secret"])
twitter_api = tweepy.API(auth)

bot = commands.Bot(command_prefix="!")


# Get info about an artist based on a previous immediate message containing a valid url from either
# twitter, danbooru or pixiv.
@bot.group(aliases=["art"])
async def artist(ctx):
    if ctx.invoked_subcommand is None:
        if art.last_artist is None:
            # Better change this to attempt to look back instead of giving up right away
            await ctx.send("I'm not aware of anybody at the moment...")
            return


@artist.command(aliases=["twit"])
async def twitter(ctx):
    embed = discord.Embed()
    embed.set_author(
        name="{} (@{})".format(art.last_artist.twitter_name, art.last_artist.twitter_screen_name),
        url="https://twitter.com/{}".format(art.last_artist.twitter_screen_name),
        icon_url=art.last_artist.twitter_profile_image_url_https
    )
    embed.set_thumbnail(url=art.last_artist.twitter_profile_image_url_https)
    embed.set_footer(
        text="Twitter",
        icon_url=data["assets"]["twitter"]["favicon"]
    )
    await ctx.send(embed=embed)


@artist.command(aliases=["dan"])
async def danbooru(ctx):
    await ctx.send("Box.")


@artist.command(aliases=["pix"])
async def pixiv(ctx):
    await ctx.send("Navi?")


# Search on danbooru!
@bot.command(name="danbooru", aliases=["dan"])
async def search_danbooru(ctx):
    await ctx.send("Searching is fun!")


@bot.command(name="temperature", aliases=["temp"])
async def report_bot_temp(ctx):
    try:
        current_temp = subprocess.run(["vcgencmd", "measure_temp"], stdout=subprocess.PIPE, universal_newlines=True)
    except FileNotFoundError:
        current_temp = subprocess.run(["sensors"], stdout=subprocess.PIPE, universal_newlines=True)
    await ctx.send(current_temp.stdout)


@bot.command(name="last")
async def talk_status(ctx):
    await ctx.send("Last channel: {}\nCurrent count there: {}".format(channel_activity.last_channel, channel_activity.count))


@bot.command(aliases=["ava"])
async def avatar(ctx):
    embed = discord.Embed()
    embed.set_image(url=ctx.message.author.avatar_url)
    embed.set_author(
        name="{} #{}".format(ctx.message.author.name, ctx.message.author.discriminator),
        icon_url=ctx.message.author.avatar_url
    )
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print("ready!")
    # Change play status to something fitting
    await bot.change_presence(activity=discord.Game(name="with books"))


@bot.event
async def on_message(msg):
    # Prevent bot from spamming itself
    if msg.author.bot:
        return

    # Test for image urls
    urls = get_urls(msg.content)
    if len(urls) > 0:
        domains = get_domains(urls)
        for i in range(len(domains)):
            domain = domains[i]
            if "twitter" in domain:
                await get_twitter_gallery(msg, urls[i])

    if channel_activity.last_channel != msg.channel.id or len(urls) > 0:
        channel_activity.last_channel = msg.channel.id
        channel_activity.count = 0

    channel_activity.count += 1

    if str(msg.channel.id) in data["rules"]["quiet_channels"]:
        if not channel_activity.warned and channel_activity.count >= data["rules"]["quiet_channels"][str(msg.channel.id)]["max_messages_without_embeds"]:
            channel_activity.warned = True
            await msg.channel.send(random.choice(data["quotes"]["quiet_channel_past_threshold"]))

    await bot.process_commands(msg)


async def get_twitter_gallery(msg, url):
    channel = msg.channel

    # Checking whether or not it contains an id
    if not "/status/" in url:
        return

    parsed_id = url.split("/status/")[1].split('?')[0]
    tweet = twitter_api.get_status(parsed_id, tweet_mode="extended")

    art.last_artist = art.Gaka()
    art.last_artist.twitter_id = tweet.author.id
    art.last_artist.twitter_name = tweet.author.name
    art.last_artist.twitter_screen_name = tweet.author.screen_name
    art.last_artist.twitter_profile_image_url_https = tweet.author.profile_image_url_https

    if not hasattr(tweet, "extended_entities") or len(tweet.extended_entities["media"]) <= 1:
        print("Preview gallery not applicable.")
        return

    print(msg.embeds)
    for e in msg.embeds:
        print(str(datetime.datetime.now()))
        print(dir(e))
        print(e.url)
    if len(msg.embeds) <= 0:
        print("I wouldn't have worked. Embeds report as 0 on the first try after inactivity on message #{} at {}.".format(msg.id, str(datetime.datetime.now())))
        # await channel.send("I wouldn't have worked")

    gallery_pics = []
    for picture in tweet.extended_entities["media"][1:]:
        if picture["type"] != "photo":
            return

        # Appending :orig to get a better image quality
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
                text="Twitter",
                icon_url=data["assets"]["twitter"]["favicon"]
            )

        await channel.send(embed=embed)


def get_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    matching_urls = re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", string)
    return matching_urls


def get_domains(array):
    domains = []

    for url in array:
        # thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
        domain = url.split("//")[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


bot.run(data["keys"]["discord"]["token"])
