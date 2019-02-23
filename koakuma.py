import asyncio
import io
import os
import random
import re
import subprocess
from datetime import datetime

import aiohttp
import commentjson
import discord
import pixivpy3
import tweepy
from discord.ext import commands
from pybooru import Danbooru

import gaka as art
import urusai as channel_activity

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(SOURCE_DIR, 'config.jsonc')) as json_file:
    data = commentjson.load(json_file)

twit_auth = tweepy.OAuthHandler(data['keys']['twitter']['consumer'], data['keys']['twitter']['consumer_secret'])
twit_auth.set_access_token(data['keys']['twitter']['token'], data['keys']['twitter']['token_secret'])
twitter_api = tweepy.API(twit_auth)

pixiv_api = pixivpy3.AppPixivAPI()
pixiv_api.login(data['keys']['pixiv']['username'], data['keys']['pixiv']['password'])

danbooru_api = Danbooru('danbooru', username=data['keys']['danbooru']['username'], api_key=data['keys']['danbooru']['key'])

bot = commands.Bot(command_prefix='!')
bot.launch_time = datetime.utcnow()


# Get info about an artist based on a previous immediate message containing a valid url from either
# twitter, danbooru or pixiv.
@bot.group(aliases=['art'])
async def artist(ctx):
    if ctx.invoked_subcommand is None:
        if art.last_artist is None:
            # Better change this to attempt to look back instead of giving up right away
            await ctx.send('I\'m not aware of anybody at the moment...')
            return


@artist.command(aliases=['twit'])
async def twitter(ctx):
    embed = discord.Embed()
    embed.set_author(
        name='%s (@%s)' % (art.last_artist.twitter_name, art.last_artist.twitter_screen_name),
        url='https://twitter.com/%s' % art.last_artist.twitter_screen_name,
        icon_url=art.last_artist.twitter_profile_image_url_https
    )
    embed.set_thumbnail(url=art.last_artist.twitter_profile_image_url_https)
    embed.set_footer(
        text='Twitter',
        icon_url=data['assets']['twitter']['favicon']
    )
    await ctx.send(embed=embed)


@artist.command(aliases=['dan'])
async def danbooru(ctx):
    await ctx.send('Box.')


@artist.command(aliases=['pix'])
async def pixiv(ctx):
    await ctx.send('Navi?')


# Search on danbooru!
@bot.command(name='danbooru', aliases=['dan'])
async def search_danbooru(ctx, *args):
    search = ' '.join(args)
    if len(args) < 6:
        search += ' order:favcount'

    posts = danbooru_api.post_list(tags=search, page=1, limit=3)
    pictures = []
    for post in posts:
        post_tags = post['tag_string_general'].split()
        for tag_lacking_preview in data['rules']['no_preview_tags']:
            if tag_lacking_preview in post_tags:
                try:
                    fileurl = post['file_url']
                except:
                    fileurl = 'https://danbooru.donmai.us' + post['source']
            else:
                fileurl = 'https://danbooru.donmai.us/posts/%i' % post['id']

        pictures.append(fileurl)
        print('\n\n')

    pictures = '\n'.join(pictures)
    if len(pictures) > 1:
        await ctx.send(pictures)
    else:
        await ctx.send("There's no matches for that...")

@bot.command(name='temperature', aliases=['temp'])
async def report_bot_temp(ctx):
    try:
        current_temp = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, universal_newlines=True)
    except FileNotFoundError:
        current_temp = subprocess.run(['sensors'], stdout=subprocess.PIPE, universal_newlines=True)
    await ctx.send(current_temp.stdout)


@bot.command(name='last')
async def talk_status(ctx):
    await ctx.send('Last channel: %s\nCurrent count there: %s' % (channel_activity.last_channel, channel_activity.count))


@bot.command(aliases=['ava'])
async def avatar(ctx):
    embed = discord.Embed()
    embed.set_image(url=ctx.message.author.avatar_url)
    embed.set_author(
        name='%s #%i' % (ctx.message.author.name, ctx.message.author.discriminator),
        icon_url=ctx.message.author.avatar_url
    )
    await ctx.send(embed=embed)

@bot.command()
async def uptime(ctx):
    delta_uptime = datetime.utcnow() - bot.launch_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    await ctx.send('I\'ve been running for %i days, %i hours, %i minutes and %i seconds.' % (days, hours, minutes, seconds))

@bot.event
async def on_ready():
    print('ready!')
    # Change play status to something fitting
    await bot.change_presence(activity=discord.Game(name='with books'))


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
            if 'twitter.com' in domain:
                await get_twitter_gallery(msg, urls[i])

            if 'pixiv.net' in domain:
                await get_pixiv_gallery(msg, urls[i])

    if channel_activity.last_channel != msg.channel.id or len(urls) > 0:
        channel_activity.last_channel = msg.channel.id
        channel_activity.count = 0

    channel_activity.count += 1

    if str(msg.channel.id) in data['rules']['quiet_channels']:
        if not channel_activity.warned and channel_activity.count >= data['rules']['quiet_channels'][str(msg.channel.id)]['max_messages_without_embeds']:
            channel_activity.warned = True
            await msg.channel.send(random.choice(data['quotes']['quiet_channel_past_threshold']))

    await bot.process_commands(msg)


async def get_twitter_gallery(msg, url):
    channel = msg.channel

    # Checking whether or not it contains an id
    if not '/status/' in url:
        return

    parsed_id = url.split('/status/')[1].split('?')[0]
    tweet = twitter_api.get_status(parsed_id, tweet_mode='extended')

    art.last_artist = art.Gaka()
    art.last_artist.twitter_id = tweet.author.id
    art.last_artist.twitter_name = tweet.author.name
    art.last_artist.twitter_screen_name = tweet.author.screen_name
    art.last_artist.twitter_profile_image_url_https = tweet.author.profile_image_url_https

    if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
        print('Preview gallery not applicable.')
        return

    print(msg.embeds)
    for e in msg.embeds:
        print(str(datetime.now()))
        print(dir(e))
        print(e.url)

    if len(msg.embeds) <= 0:
        print('I wouldn\'t have worked. Embeds report as 0 on the first try after inactivity on message #%i at %s.' % (msg.id, str(datetime.now())))
        # await channel.send('I wouldn't have worked')

    gallery_pics = []
    for picture in tweet.extended_entities['media'][1:]:
        if picture['type'] != 'photo':
            return

        # Appending :orig to get a better image quality
        gallery_pics.append(picture['media_url_https'] + ':orig')

    gallery_pics_total = len(gallery_pics)
    for picture in gallery_pics:
        gallery_pics_total -= 1

        embed = discord.Embed()
        embed.set_author(
            name='%s (@%s)' % (tweet.author.name, tweet.author.screen_name),
            url='https://twitter.com/%s' % tweet.author.screen_name,
            icon_url=tweet.author.profile_image_url_https
        )
        embed.set_image(url=picture)

        # If it's the last picture to show, add a brand footer
        if gallery_pics_total <= 0:
            embed.set_footer(
                text='Twitter',
                icon_url=data['assets']['twitter']['favicon']
            )

        await channel.send(embed=embed)


async def get_pixiv_gallery(msg, url):
    channel = msg.channel

    # Checking whether or not it contains an id
    if not 'illust_id=' in url:
        return

    parsed_id = url.split('illust_id=')[1].split('&')[0]
    print('Now starting to process pixiv link #%s' % parsed_id)
    illust_json = pixiv_api.illust_detail(parsed_id, req_auth=True)
    print(illust_json)
    if 'error' in illust_json:
        # await channel.send('Invalid id')
        # Attempt to login
        pixiv_api.login(data['keys']['pixiv']['username'], data['keys']['pixiv']['password'])
        illust_json = pixiv_api.illust_detail(parsed_id, req_auth=True)
        print(illust_json)

        if 'error' in illust_json:
            # too bad
            print('Invalid Pixiv id')
            return

    print('Pixiv auth passed! (for #%s)' % parsed_id)

    illust = illust_json.illust
    meta_dir = None

    if illust['meta_single_page']:
        meta_dir = 'meta_single_page'
    elif illust['meta_pages']:
        meta_dir = 'meta_pages'
    else:
        await channel.send('Sorry, sorry, sorry! Link missing data!')
        return

    temp_wait = await channel.send('***%s***' % random.choice(data['quotes']['processing_long_task']))

    embed = discord.Embed()
    embed.set_thumbnail(url=msg.author.avatar_url)
    embed.description = '%s said...\n\n%s' % (msg.author.mention, msg.content)
    await channel.send(embed=embed)

    await msg.delete()
    print('Retrieving first picture for #%s' % parsed_id)

    async with aiohttp.ClientSession() as session:
        img_bytes = await fetch_image(session, illust['image_urls']['medium'], {'Referer': 'https://app-api.pixiv.net/'})

    print('Retrieved #%s (maybe)' % parsed_id)

    image_name = 'pixiv_img.png'
    embed = discord.Embed()
    embed.set_author(
        name=illust['user']['name'],
        url='https://www.pixiv.net/member.php?id=%i' % illust['user']['id']
    )
    embed.title = illust.title
    embed.url = url
    if not illust.caption:
        embed.description = '%s by %s' % (illust.title, illust['user']['name'])
    else:
        embed.description = illust.caption
    embed.set_image(url='attachment://%s' % image_name)
    await channel.send(file=discord.File(fp=img_bytes, filename=image_name), embed=embed)

    if len(illust[meta_dir]) <= 1:
        await temp_wait.delete()
        print('DONE PIXIV!')
        return

    for picture in illust[meta_dir][1:4]:
        print('Retrieving more pictures from #%s...' % parsed_id)
        async with aiohttp.ClientSession() as session:
            img_bytes = await fetch_image(session, picture.image_urls['medium'], {'Referer': 'https://app-api.pixiv.net/'})
        print('Retrieved more from #%s (maybe)' % parsed_id)
        image_name = 'pixiv_img.png'
        embed = discord.Embed()
        embed.set_author(
            name=illust['user']['name'],
            url='https://www.pixiv.net/member.php?id=%i' % illust['user']['id']
        )
        embed.set_image(url='attachment://%s' % image_name)
        await channel.send(file=discord.File(fp=img_bytes, filename=image_name), embed=embed)

    await temp_wait.delete()
    print('DONE PIXIV!')


async def fetch_image(session, url, headers={}):
    async with session.get(url, headers=headers) as response:
        img_bytes = io.BytesIO(await response.read())
        return img_bytes


def get_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    matching_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return matching_urls


def get_domains(array):
    domains = []

    for url in array:
        # thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
        domain = url.split('//')[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


bot.run(data['keys']['discord']['token'])
