"""Commands for streaming services like Twitch and Picarto"""
import os
import re

import discord
from discord.ext import commands

import koabot.utils.net as net_utils
import koabot.utils.posts as post_utils
from koabot import koakuma
from koabot.cogs.botstatus import BotStatus


class StreamService(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._twitch_access_token: str = None
        self._twitch_headers = None

    @commands.command(name='twitch')
    async def search_twitch(self, ctx: commands.Context, *args):
        """Search on Twitch"""
        if len(args) < 1:
            print('well it worked...')
            return

        action = args[0]

        if action == 'get':
            embed = discord.Embed()
            embed.description = ''
            embed.set_footer(
                text=self.bot.assets['twitch']['name'],
                icon_url=self.bot.assets['twitch']['favicon'])

            # !twitch get <NAME> or !twich get <ID>
            if len(args) == 2:
                item = args[1]
                if re.findall(r'(^[0-9]+$)', item):
                    # is searching an id
                    search_type = 'user_id'
                else:
                    # searching an username
                    search_type = 'user_login'

                response = await net_utils.http_request(f'https://api.twitch.tv/helix/streams?{search_type}={item}', headers=await self.twitch_headers, json=True)
                streams = response.json

                for stream in streams['data'][:3]:
                    await ctx.send(f"{stream['user_login']} ({stream['user_id']})\nhttps://twitch.tv/{stream['user_name']}")

            # fetch list from twitch
            else:
                response = await net_utils.http_request('https://api.twitch.tv/helix/streams', headers=await self.twitch_headers, json=True)
                streams = response.json

                for stream in streams['data'][:5]:
                    embed.description += f"stream \"{stream['title']}\"\nstreamer {stream['user_name']} ({stream['user_id']})\n\n"

                await ctx.send(embed=embed)

    async def get_picarto_stream_preview(self, msg: discord.Message, url: str):
        """Automatically fetch a preview of the running stream"""

        channel: discord.TextChannel = msg.channel
        channel_name = post_utils.get_name_or_id(url, start='.tv/')

        bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        if not channel_name:
            return

        channel_url = f'https://api.picarto.tv/api/v1/channel/name/{channel_name}'
        picarto_request = (await net_utils.http_request(channel_url, json=True)).json

        if not picarto_request:
            await channel.send(bot_cog.get_quote('stream_preview_failed'))
            return

        if not picarto_request['online']:
            await channel.send(bot_cog.get_quote('stream_preview_offline'))
            return

        image = await net_utils.fetch_image(picarto_request['thumbnails']['web'])
        filename = net_utils.get_url_filename(picarto_request['thumbnails']['web'])

        embed = discord.Embed()
        embed.set_author(
            name=channel_name,
            url=f'https://picarto.tv/{channel_name}',
            icon_url=picarto_request['avatar'])
        embed.description = f"**{picarto_request['title']}**"
        embed.set_image(url=f'attachment://{filename}')
        embed.set_footer(
            text=self.bot.assets['picarto']['name'],
            icon_url=self.bot.assets['picarto']['favicon'])
        await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)
        return True

    @property
    async def twitch_headers(self):
        """The headers needed to make requests to Twitch"""
        self._twitch_headers = {'Client-ID': self.bot.auth_keys['twitch']['client_id'], 'Authorization': f'Bearer {await self.twitch_access_token}'}
        return self._twitch_headers

    @property
    async def twitch_access_token(self) -> str:
        """The access token needed to become authorized to make requests to Twitch"""
        if self._twitch_access_token:
            return self._twitch_access_token

        return await self.fetch_twitch_access_token()

    async def fetch_twitch_access_token(self, force=False):
        """Get access token saved locally or from Twitch
        Arguments:
            force::bool
                Ignore the cached key and fetch a new one from Twitch
        """
        token_filename = 'access_token'
        twitch_cache_dir = os.path.join(koakuma.CACHE_DIR, 'twitch')
        token_path = os.path.join(twitch_cache_dir, token_filename)

        # if the file exists
        if os.path.exists(token_path) and not force:
            with open(token_path, encoding="UTF-8") as token_file:
                self._twitch_access_token = token_file.readline()

        if not self._twitch_access_token or force:
            url = 'https://id.twitch.tv/oauth2/token'
            data = {
                'client_id': self.bot.auth_keys['twitch']['client_id'],
                'client_secret':  self.bot.auth_keys['twitch']['client_secret'],
                'grant_type': 'client_credentials'}
            response = (await net_utils.http_request(url, post=True, data=data, json=True)).json

            os.makedirs(twitch_cache_dir, exist_ok=True)

            with open(token_path, 'w', encoding="UTF-8") as token_file:
                self._twitch_access_token = response['access_token']
                token_file.write(self._twitch_access_token)

        return self._twitch_access_token


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(StreamService(bot))
