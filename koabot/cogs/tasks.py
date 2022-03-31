"""Routine tasks"""
import asyncio
from datetime import datetime

import discord
from discord.ext import commands

import koabot.core.net as net_core
from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.cogs.streamservice import StreamAnnouncement, StreamService
from koabot.kbot import KBot


class Tasks(commands.Cog):
    """Periodic task runner"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def streamservice(self) -> StreamService:
        return self.bot.get_cog('StreamService')

    async def cog_load(self):
        """The tasks to be run at boot"""
        self.bot.loop.create_task(self.check_live_streamers())
        self.bot.loop.create_task(self.change_presence_periodically())

    async def change_presence_periodically(self) -> None:
        """Changes presence at X time, once per day"""

        day: int = datetime.utcnow().day

        while not self.bot.is_closed():
            time = datetime.utcnow()

            # if it's time and it's not the same day
            if time.hour == self.bot.tasks['presence_change']['utc_hour'] and time.day != day:
                day = time.day
                await self.bot.change_presence(activity=discord.Game(name=self.botstatus.get_quote('playing_status')))

            # check twice an hour
            await asyncio.sleep(60 * 30)

    async def lookup_pending_posts(self) -> None:
        """Every 5 minutes search for danbooru posts"""

        # await self.bot.wait_until_ready()

        guide = self.bot.guides['gallery']['danbooru-default']
        pending_posts = []
        channel_categories = {}

        for channel_category, channel_list in self.bot.tasks['danbooru']['channels'].items():
            channel_categories[channel_category] = []
            for channel in channel_list:
                channel_categories[channel_category].append(self.bot.get_channel(int(channel)))

        while not self.bot.is_closed():
            botstatus_cog = self.botstatus
            posts = (await self.board.search_query(tags=self.bot.tasks['danbooru']['tag_list'], guide=guide, limit=5, random=True)).json

            safe_posts = []
            nsfw_posts = []
            for post in posts:
                if not (post_id := post['id']) in pending_posts:
                    pending_posts.append(post_id)
                    post_url = guide['post']['url'].format(post_id)

                    if post['rating'] == 's':
                        safe_posts.append(post_url)
                    else:
                        nsfw_posts.append(post_url)

            safe_posts = '\n'.join(safe_posts)
            nsfw_posts = '\n'.join(nsfw_posts)

            if safe_posts or nsfw_posts:
                for channel in channel_categories['safe_channels']:
                    await channel.send(botstatus_cog.get_quote('posts_to_approve') + '\n' + safe_posts)

            if nsfw_posts:
                for channel in channel_categories['nsfw_channels']:
                    await channel.send(botstatus_cog.get_quote('posts_to_approve') + '\n' + nsfw_posts)

            # check every 5 minutes
            await asyncio.sleep(60 * 5)

    async def check_live_streamers(self) -> None:
        """Checks every so often for streamers that have gone online"""

        # await self.bot.wait_until_ready()

        online_streamers = []

        while not self.bot.is_closed():
            streamservice_cog = self.streamservice

            temp_online = []
            for streamer in online_streamers:
                if streamer['preserve']:
                    streamer['preserve'] = False
                    temp_online.append(streamer)

            online_streamers = temp_online

            twitch_search = 'https://api.twitch.tv/helix/streams?'

            for streamer in self.bot.tasks['streamer_activity']['streamers']:
                match streamer['platform']:
                    case 'twitch':
                        twitch_search += f"user_id={streamer['user_id']}&"

            twitch_query = await net_core.http_request(twitch_search, headers=await streamservice_cog.twitch_headers, json=True)

            match twitch_query.status:
                case 401:
                    # Token is invalid/expired, acquire a new token
                    await streamservice_cog.fetch_twitch_access_token(force=True)

                    twitch_query = await net_core.http_request(twitch_search, headers=await streamservice_cog.twitch_headers, json=True)

            for streamer in twitch_query.json['data']:
                already_online = False

                for online_streamer in online_streamers:
                    if streamer['id'] == online_streamer['streamer']['id']:
                        # streamer is already online, and it was already reported
                        online_streamer['preserve'] = True
                        online_streamer['announced'] = True
                        already_online = True
                        break

                if already_online:
                    continue

                for config_streamer in self.bot.tasks['streamer_activity']['streamers']:
                    if streamer['user_id'] == str(config_streamer['user_id']):
                        natural_name: str = config_streamer.get('casual_name', streamer['user_name'])
                        break

                online_streamers.append({'platform': 'twitch', 'streamer': streamer,
                                        'name': natural_name, 'preserve': True, 'announced': False})

            stream_announcements: list[StreamAnnouncement] = []
            for streamer in online_streamers:
                if streamer['announced']:
                    continue

                embed = discord.Embed()
                embed.set_author(
                    name=streamer['streamer']['user_name'],
                    url=f"https://www.twitch.tv/{streamer['streamer']['user_name']}")
                embed.set_footer(
                    text=self.bot.assets['twitch']['name'],
                    icon_url=self.bot.assets['twitch']['favicon'])

                # setting thumbnail size
                thumbnail_url: str = streamer['streamer']['thumbnail_url']
                thumbnail_url = thumbnail_url.replace("{width}", "600").replace("{height}", "350")
                thumbnail_filename = net_core.get_url_filename(thumbnail_url)
                image = await net_core.fetch_image(thumbnail_url)
                embed.set_image(url=f"attachment://{thumbnail_filename}")

                stream_announcements.append(
                    StreamAnnouncement(streamer_name=streamer['name'],
                                       filename=thumbnail_filename,
                                       image=image,
                                       embed=embed))

            for channel_id in self.bot.tasks['streamer_activity']['channels_to_announce_on']:
                channel: discord.TextChannel = self.bot.get_channel(channel_id)
                for batch in stream_announcements:
                    await batch.send_announcement(channel)

            # check every 5 minutes
            await asyncio.sleep(60 * 5)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Tasks(bot))
