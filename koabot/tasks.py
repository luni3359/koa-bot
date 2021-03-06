"""Routine tasks"""
import asyncio
import random
from datetime import datetime

import discord

import koabot.utils as utils
import koabot.utils.net
from koabot import koakuma


async def check_live_streamers():
    """Checks every so often for streamers that have gone online"""

    await koakuma.bot.wait_until_ready()

    streamservice_cog = koakuma.bot.get_cog('StreamService')
    online_streamers = []

    while not koakuma.bot.is_closed():
        temp_online = []
        for streamer in online_streamers:
            if streamer['preserve']:
                streamer['preserve'] = False
                temp_online.append(streamer)

        online_streamers = temp_online

        twitch_search = 'https://api.twitch.tv/helix/streams?'

        for streamer in koakuma.bot.tasks['streamer_activity']['streamers']:
            if streamer['platform'] == 'twitch':
                twitch_search += f"user_id={streamer['user_id']}&"

        twitch_query = await utils.net.http_request(twitch_search, headers=await streamservice_cog.twitch_headers, json=True)

        # Token is invalid/expired, acquire a new token
        if twitch_query.status == 401:
            await streamservice_cog.fetch_twitch_access_token(force=True)

            twitch_query = await utils.net.http_request(twitch_search, headers=await streamservice_cog.twitch_headers, json=True)

        for streamer in twitch_query.json['data']:
            already_online = False

            for on_streamer in online_streamers:
                if streamer['id'] == on_streamer['streamer']['id']:
                    # streamer is already online, and it was already reported
                    on_streamer['preserve'] = True
                    on_streamer['announced'] = True
                    already_online = True

            if already_online:
                continue

            for config_streamers in koakuma.bot.tasks['streamer_activity']['streamers']:
                if streamer['user_id'] == str(config_streamers['user_id']):
                    natural_name = 'casual_name' in config_streamers and config_streamers['casual_name'] or streamer['user_name']
                    break

            online_streamers.append({'platform': 'twitch', 'streamer': streamer, 'name': natural_name, 'preserve': True, 'announced': False})

        stream_announcements = []
        for streamer in online_streamers:
            if streamer['announced']:
                continue

            embed = discord.Embed()
            embed.set_author(
                name=streamer['streamer']['user_name'],
                url=f"https://www.twitch.tv/{streamer['streamer']['user_name']}")
            embed.set_footer(
                text=koakuma.bot.assets['twitch']['name'],
                icon_url=koakuma.bot.assets['twitch']['favicon'])

            # setting thumbnail size
            thumbnail_url = streamer['streamer']['thumbnail_url']
            thumbnail_url = thumbnail_url.replace('{width}', '600')
            thumbnail_url = thumbnail_url.replace('{height}', '350')
            thumbnail_filename = utils.net.get_url_filename(thumbnail_url)
            image = await utils.net.fetch_image(thumbnail_url)
            embed.set_image(url=f'attachment://{thumbnail_filename}')

            stream_announcements.append({'message': f"{streamer['name']} is now live!", 'embed': embed, 'image': image, 'filename': thumbnail_filename})

        for channel in koakuma.bot.tasks['streamer_activity']['channels_to_announce_on']:
            for batch in stream_announcements:
                channel = koakuma.bot.get_channel(channel)
                if 'image' in batch:
                    await channel.send(batch['message'], file=discord.File(fp=batch['image'], filename=batch['filename']), embed=batch['embed'])
                else:
                    await channel.send(batch['message'], embed=batch['embed'])

        # check every 5 minutes
        await asyncio.sleep(60 * 5)


async def change_presence_periodically():
    """Changes presence at X time, once per day"""

    await koakuma.bot.wait_until_ready()

    day = datetime.utcnow().day

    while not koakuma.bot.is_closed():
        time = datetime.utcnow()

        # if it's time and it's not the same day
        if time.hour == koakuma.bot.tasks['presence_change']['utc_hour'] and time.day != day:
            day = time.day
            await koakuma.bot.change_presence(activity=discord.Game(name=random.choice(koakuma.bot.quotes['playing_status'])))

        # check twice an hour
        await asyncio.sleep(60 * 30)


async def lookup_pending_posts():
    """Every 5 minutes search for danbooru posts"""

    await koakuma.bot.wait_until_ready()

    board_cog = koakuma.bot.get_cog('Board')
    pending_posts = []
    channel_categories = {}

    for channel_category, channel_list in koakuma.bot.tasks['danbooru']['channels'].items():
        channel_categories[channel_category] = []
        for channel in channel_list:
            channel_categories[channel_category].append(koakuma.bot.get_channel(int(channel)))

    while not koakuma.bot.is_closed():
        posts = (await board_cog.search_query(tags=koakuma.bot.tasks['danbooru']['tag_list'], limit=5, random=True)).json

        safe_posts = []
        nsfw_posts = []
        for post in posts:
            post_id = post['id']
            if not post_id in pending_posts:
                pending_posts.append(post_id)
                url_to_append = koakuma.bot.assets['danbooru']['search_url'].format(post_id)

                if post['rating'] == 's':
                    safe_posts.append(url_to_append)
                else:
                    nsfw_posts.append(url_to_append)

        safe_posts = '\n'.join(safe_posts)
        nsfw_posts = '\n'.join(nsfw_posts)

        if safe_posts or nsfw_posts:
            for channel in channel_categories['safe_channels']:
                await channel.send(random.choice(koakuma.bot.quotes['posts_to_approve']) + '\n' + safe_posts)

        if nsfw_posts:
            for channel in channel_categories['nsfw_channels']:
                await channel.send(random.choice(koakuma.bot.quotes['posts_to_approve']) + '\n' + nsfw_posts)

        # check every 5 minutes
        await asyncio.sleep(60 * 5)
