"""Music functions!"""
import asyncio
import random
import re
from pathlib import Path

import discord
import yt_dlp as youtube_dl
from discord.ext import commands

from koabot.kbot import KBot
from koabot.patterns import URL_PATTERN

ydl_opts = {
    'format': "bestaudio/best",
    'restrictfilenames': True,
    'source_address': "0.0.0.0"
}
ytdl = youtube_dl.YoutubeDL(ydl_opts)


class YTDLSource(discord.PCMVolumeTransformer):
    """Found on the internet
    https://stackoverflow.com/a/56709893/7688278
    look into this https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
    """

    def __init__(self, source: discord.AudioSource, *, data, volume=0.5) -> None:
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, timestamp=0):
        """Retrieve audio stream from an url"""
        loop = loop or asyncio.get_event_loop()
        data: dict = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        ffmpeg_opts = {
            'options': f"-vn -ss {timestamp}"
        }

        yt_url: re.Match = re.search(r'watch\?v=([a-zA-Z0-9_-]{10,12})', url)

        if not yt_url:
            return None

        yt_id: str = yt_url.group(1)
        video_data: dict

        if 'entries' not in data:
            video_data = data
        else:
            # in case the video in url is not in the playlist
            video_data = data['entries'][0]

            # take video from url instead of an element from the playlist
            for entry in data['entries']:
                if entry['id'] == yt_id:
                    video_data = entry
                    break

        filename: str = video_data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_opts), data=video_data)


class Music(commands.Cog):
    """Play music"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    def get_timestamp(self, url: str) -> int:
        """Fetches the timestamp in seconds from the provided url"""
        timestamp = re.search(r'\?t=([0-9]+)', url)
        if not timestamp:
            return 0
        return int(timestamp.group(1))

    def now_playing_str(self, string) -> str:
        """Formats the given string to include 'Now playing'"""
        return f"Now playing **{string}**"

    async def join_channel(self, ctx: commands.Context, voice_client: discord.VoiceClient, voice_state: discord.VoiceState):
        """Joins a channel based on the situation"""
        if not voice_client:
            if voice_state:
                voice_client: discord.VoiceChannel = await voice_state.channel.connect()
                await ctx.reply(f"Connected to **\"{voice_state.channel.name}\"** (your voice channel)!", mention_author=False)
            else:
                if not ctx.guild.voice_channels:
                    await ctx.reply("There's no voice channels in this server...", mention_author=False)
                    return

                for voice_channel in ctx.guild.voice_channels:
                    voice_client: discord.VoiceClient = await voice_channel.connect()
                    await ctx.reply(f"Connected to **\"{voice_channel.name}\"** (the nearest voice channel)!", mention_author=False)
                    break
        else:
            if voice_state:
                if voice_client.channel != voice_state.channel:
                    await voice_client.move_to(voice_state.channel)
                    await ctx.reply(f"Moved to **\"{voice_state.channel.name}\"** (your voice channel)!", mention_author=False)
                else:
                    await ctx.reply(f"I'm already in **\"{voice_state.channel.name}\"** (your voice channel)!", mention_author=False)

    @commands.hybrid_command()
    async def join(self, ctx: commands.Context):
        """Joins a voice channel"""
        await self.join_channel(ctx, ctx.voice_client, ctx.author.voice)

    @commands.hybrid_command()
    async def leave(self, ctx: commands.Context):
        """Leaves a voice channel"""
        voice_client: discord.VoiceClient = ctx.voice_client

        if voice_client:
            await voice_client.disconnect()
            await ctx.send(f"Disconnected from **\"{voice_client.channel.name}\"**!")
        else:
            await ctx.send("No voice channel to disconnect from...")

    @commands.hybrid_command()
    async def play(self, ctx: commands.Context, *, search_or_url: str = ""):
        """Plays a track (overrides current track)"""
        # TODO https://stackoverflow.com/a/62360149/7688278
        # Allow links to play from specified timestamps
        voice_client: discord.VoiceClient = ctx.voice_client

        if not voice_client:
            return await ctx.reply("I'm not in a voice channel!", mention_author=False)

        if len(search_or_url) == 0:
            # test a random url while in development
            url = random.choice(self.bot.testing['vc']['yt-suggestions'])
        else:
            # assuming it's always an url for now
            url = URL_PATTERN.findall(search_or_url)[0]

        async with ctx.typing():
            timestamp = self.get_timestamp(url)
            stream: YTDLSource = await YTDLSource.from_url(url, loop=self.bot.loop, timestamp=timestamp)
            voice_client.play(stream, after=lambda e: print("Stream error.") if e else None)

        if voice_client.is_playing:
            await ctx.reply(self.now_playing_str(stream.title), mention_author=False)
            await ctx.message.edit(suppress=True)

    @commands.hybrid_command()
    async def stop(self, ctx: commands.Context):
        """Stops the current track"""
        voice_client: discord.VoiceClient = ctx.voice_client

        if voice_client and voice_client.is_playing():
            await ctx.reply("Stopping track.", mention_author=False)
            voice_client.stop()
        else:
            await ctx.reply("No track is playing.", mention_author=False)

    @commands.hybrid_command()
    async def echo(self, ctx: commands.Context):
        """Echoes sound"""

    @commands.hybrid_command()
    async def test(self, ctx: commands.Context):
        """Music test"""
        voice_client: discord.VoiceClient = ctx.voice_client

        # join a voice channel
        await self.join_channel(ctx, voice_client, ctx.author.voice)

        music_file = Path(self.bot.PROJECT_DIR, "assets", self.bot.testing['vc']['music-file'])
        source = discord.FFmpegPCMAudio(music_file)

        print("playing music now!")
        if voice_client.is_playing():
            print("stopping music...")
            voice_client.stop()

        print("playing...")
        voice_client.play(source, after=lambda e: print("Done playing sound file.", e))


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Music(bot))
