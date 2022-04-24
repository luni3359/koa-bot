"""Commands for streaming services like Twitch and Picarto"""
import re
from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.cogs.botstatus import BotStatus
from koabot.kbot import KBot


class StreamAnnouncement():
    def __init__(self, *, streamer_name: str, filename: str, image: BytesIO, embed: discord.Embed) -> None:
        self.streamer_name = streamer_name
        self.filename = filename
        self.image = image
        self.embed = embed

    def get_message(self) -> str:
        return f"{self.streamer_name} is now live!"

    async def send_announcement(self, channel: discord.TextChannel) -> discord.Message:
        if self.image:
            return await channel.send(self.get_message(), file=discord.File(fp=self.image, filename=self.filename), embed=self.embed)
        return await channel.send(self.get_message(), embed=self.embed)


class StreamService(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

        self._twitch_headers: dict = None
        self._twitch_access_token: str = None

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    async def twitch_headers(self) -> dict:
        """The headers needed to make requests to Twitch"""
        if not self._twitch_headers:
            client_id = self.bot.auth_keys['twitch']['client_id']
            self._twitch_headers = {'Client-ID': client_id, 'Authorization': f'Bearer {await self.twitch_access_token}'}

        return self._twitch_headers

    @property
    async def twitch_access_token(self) -> str:
        """The access token needed to become authorized to make requests to Twitch"""
        if not self._twitch_access_token:
            self._twitch_access_token = await self.fetch_twitch_access_token()

        return self._twitch_access_token

    async def fetch_twitch_access_token(self, force=False) -> str:
        """Get access token saved locally or from Twitch
        Arguments:
            force::bool
                Ignore the cached key and fetch a new one from Twitch
        """
        twitch_access_token: str = None
        token_filename = 'access_token'
        twitch_cache_dir = Path(self.bot.CACHE_DIR, "twitch")
        token_path = Path(twitch_cache_dir, token_filename)

        # if the file exists
        if token_path.exists() and not force:
            with open(token_path, encoding="UTF-8") as token_file:
                twitch_access_token = token_file.readline()

        if not twitch_access_token or force:
            twitch_keys = self.bot.auth_keys['twitch']
            url = 'https://id.twitch.tv/oauth2/token'
            data = {
                'client_id': twitch_keys['client_id'],
                'client_secret':  twitch_keys['client_secret'],
                'grant_type': 'client_credentials'}

            twitch_cache_dir.mkdir(exist_ok=True)
            response = (await net_core.http_request(url, post=True, data=data, json=True)).json

            with open(token_path, 'w', encoding="UTF-8") as token_file:
                twitch_access_token = response['access_token']
                token_file.write(twitch_access_token)

        return twitch_access_token

    @commands.command(name='twitch')
    async def search_twitch(self, ctx: commands.Context, *args):
        """Search on Twitch"""
        guide = self.bot.assets['twitch']

        if len(args) < 1:
            print('well it worked...')
            return

        # action = args[0]

        match args[0]:
            case 'get':
                twitch_api_url = "https://api.twitch.tv/helix/streams"
                embed = discord.Embed()
                embed.description = ''
                embed.set_footer(text=guide['name'], icon_url=guide['favicon'])

                # !twitch get <NAME> or !twich get <ID>
                if len(args) == 2:
                    item = args[1]
                    if re.findall(r'(^[0-9]+$)', item):
                        # is searching an id
                        search_type = 'user_id'
                    else:
                        # searching an username
                        search_type = 'user_login'

                    response = await net_core.http_request(f"{twitch_api_url}?{search_type}={item}", headers=await self.twitch_headers, json=True)
                    streams = response.json

                    for stream in streams['data'][:3]:
                        await ctx.send(f"{stream['user_login']} ({stream['user_id']})\nhttps://twitch.tv/{stream['user_name']}")

                # fetch list from twitch
                else:
                    response = await net_core.http_request(twitch_api_url, headers=await self.twitch_headers, json=True)
                    streams = response.json

                    for stream in streams['data'][:5]:
                        embed.description += f"stream \"{stream['title']}\"\nstreamer {stream['user_name']} ({stream['user_id']})\n\n"

                    await ctx.send(embed=embed)

    async def get_picarto_stream_preview(self, msg: discord.Message, url: str, /, *, orig_to_be_deleted: bool = False) -> bool:
        """Automatically fetch a preview of the running stream
        Arguments:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the picarto stream
        Keywords:
            orig_to_be_deleted::bool
                Whether or not the message that invoked this preview is marked for deletion
        Returns:
            preview_was_successfuly_sent::bool
        """
        guide = self.bot.assets['picarto']
        channel: discord.TextChannel = msg.channel

        if not (channel_name := post_core.get_name_or_id(url, start='.tv/')):
            return False

        channel_url = f"https://api.picarto.tv/api/v1/channel/name/{channel_name}"

        if not (picarto_request := (await net_core.http_request(channel_url, json=True)).json):
            await channel.send(self.botstatus.get_quote('stream_preview_failed'))
            return False

        if not picarto_request['online']:
            await channel.send(self.botstatus.get_quote('stream_preview_offline'))
            return False

        image = await net_core.fetch_image(picarto_request['thumbnails']['web'])
        filename: str = net_core.get_url_filename(picarto_request['thumbnails']['web'])

        embed = discord.Embed()
        embed.set_author(
            name=channel_name,
            url=f'https://picarto.tv/{channel_name}',
            icon_url=picarto_request['avatar'])
        embed.description = f"**{picarto_request['title']}**"
        embed.set_image(url=f'attachment://{filename}')
        embed.set_footer(text=guide['name'], icon_url=guide['favicon'])

        if orig_to_be_deleted:
            await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)
        else:
            try:
                await msg.edit(suppress=True)
            except discord.errors.Forbidden as e:
                # Missing Permissions
                match e.code:
                    case 50013:
                        print("Missing Permissions: Cannot suppress embed from sender's message")
                    case _:
                        print(f"Forbidden: Status {e.status} (code {e.code}")
            await msg.reply(file=discord.File(fp=image, filename=filename), embed=embed, mention_author=False)

        return True


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(StreamService(bot))
