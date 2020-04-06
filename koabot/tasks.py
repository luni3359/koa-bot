"""Routine tasks"""
import asyncio
import random
from datetime import datetime

import discord

import koabot.board
import koabot.koakuma
import koabot.utils.net


async def check_live_streamers():
    """Checks every so often for streamers that have gone online"""

    await koabot.koakuma.bot.wait_until_ready()

    online_streamers = []

    while not koabot.koakuma.bot.is_closed():
        temp_online = []
        for streamer in online_streamers:
            if streamer['preserve']:
                streamer['preserve'] = False
                temp_online.append(streamer)

        online_streamers = temp_online

        twitch_search = 'https://api.twitch.tv/helix/streams?'

        for streamer in koabot.koakuma.bot.tasks['streamer_activity']['streamers']:
            if streamer['platform'] == 'twitch':
                twitch_search += 'user_id=%s&' % streamer['user_id']

        twitch_query = await koabot.utils.net.http_request(twitch_search, headers=koabot.koakuma.bot.assets['twitch']['headers'], json=True)

        for streamer in twitch_query['data']:
            already_online = False

            for on_streamer in online_streamers:
                if streamer['id'] == on_streamer['streamer']['id']:
                    # streamer is already online, and it was already reported
                    on_streamer['preserve'] = True
                    on_streamer['announced'] = True
                    already_online = True

            if already_online:
                continue

            for config_streamers in koabot.koakuma.bot.tasks['streamer_activity']['streamers']:
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
                url='https://www.twitch.tv/' + streamer['streamer']['user_name'])
            embed.set_footer(
                text=koabot.koakuma.bot.assets['twitch']['name'],
                icon_url=koabot.koakuma.bot.assets['twitch']['favicon'])

            # setting thumbnail size
            thumbnail_url = streamer['streamer']['thumbnail_url']
            thumbnail_url = thumbnail_url.replace('{width}', '600')
            thumbnail_url = thumbnail_url.replace('{height}', '350')
            thumbnail_filename = koabot.utils.net.get_url_filename(thumbnail_url)
            image = await koabot.utils.net.fetch_image(thumbnail_url)
            embed.set_image(url='attachment://' + thumbnail_filename)

            stream_announcements.append({'message': '%s is now live!' % streamer['name'], 'embed': embed, 'image': image, 'filename': thumbnail_filename})

        for channel in koabot.koakuma.bot.tasks['streamer_activity']['channels_to_announce_on']:
            for batch in stream_announcements:
                channel = koabot.koakuma.bot.get_channel(channel)
                if 'image' in batch:
                    await channel.send(batch['message'], file=discord.File(fp=batch['image'], filename=batch['filename']), embed=batch['embed'])
                else:
                    await channel.send(batch['message'], embed=batch['embed'])

        # check every 5 minutes
        await asyncio.sleep(60)


async def change_presence_periodically():
    """Changes presence at X time, once per day"""

    await koabot.koakuma.bot.wait_until_ready()

    day = datetime.utcnow().day

    while not koabot.koakuma.bot.is_closed():
        time = datetime.utcnow()

        # if it's time and it's not the same day
        if time.hour == koabot.koakuma.bot.tasks['presence_change']['utc_hour'] and time.day != day:
            day = time.day
            await koabot.koakuma.bot.change_presence(activity=discord.Game(name=random.choice(koabot.koakuma.bot.quotes['playing_status'])))

        # check twice an hour
        await asyncio.sleep(60 * 30)


async def lookup_pending_posts():
    """Every 5 minutes search for danbooru posts"""

    await koabot.koakuma.bot.wait_until_ready()

    pending_posts = []
    channel_categories = {}

    for channel_category, channel_list in koabot.koakuma.bot.tasks['danbooru']['channels'].items():
        channel_categories[channel_category] = []
        for channel in channel_list:
            channel_categories[channel_category].append(koabot.koakuma.bot.get_channel(int(channel)))

    while not koabot.koakuma.bot.is_closed():
        posts = await koabot.board.board_search(tags=koabot.koakuma.bot.tasks['danbooru']['tag_list'], limit=5, random=True)

        safe_posts = []
        nsfw_posts = []
        for post in posts:
            if not post['id'] in pending_posts:
                pending_posts.append(post['id'])
                url_to_append = 'https://danbooru.donmai.us/posts/%i' % post['id']

                if post['rating'] is 's':
                    safe_posts.append(url_to_append)
                else:
                    nsfw_posts.append(url_to_append)

        safe_posts = '\n'.join(safe_posts)
        nsfw_posts = '\n'.join(nsfw_posts)

        if safe_posts or nsfw_posts:
            for channel in channel_categories['safe_channels']:
                await channel.send(random.choice(koabot.koakuma.bot.quotes['posts_to_approve']) + '\n' + safe_posts)

        if nsfw_posts:
            for channel in channel_categories['nsfw_channels']:
                await channel.send(random.choice(koabot.koakuma.bot.quotes['posts_to_approve']) + '\n' + nsfw_posts)

        await asyncio.sleep(60 * 5)
