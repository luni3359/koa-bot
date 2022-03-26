"""Music functions!"""
import asyncio
import os
import random
import re

import discord
import yt_dlp as youtube_dl
from discord.ext import commands

from koabot.kbot import KBot
from koabot.patterns import URL_PATTERN

ydl_opts = {
    'format': "bestaudio/best",
    'source_address': "0.0.0.0"
}
ffmpeg_opts = {
    'options': "-vn"
}
ytdl = youtube_dl.YoutubeDL(ydl_opts)


class YTDLSource(discord.PCMVolumeTransformer):
    """Found on the internet

    https://stackoverflow.com/a/56709893/7688278
    look into this https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
    """

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        """Retrieve audio stream from an url"""
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_opts), data=data)


class Music(commands.Cog):
    """Play music"""

    def __init__(self, bot: KBot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx: commands.Context):
        """Joins a voice channel"""
        voice_client: discord.VoiceClient = ctx.voice_client
        author_voicestate: discord.VoiceState = ctx.author.voice

        if not voice_client:
            if author_voicestate:
                voice_client: discord.VoiceChannel = await author_voicestate.channel.connect()
                await ctx.send(f"Connected to **\"{author_voicestate.channel.name}\"** (your voice channel)!")
            else:
                if not ctx.guild.voice_channels:
                    await ctx.send("There's no voice channels in this server...")
                    return

                for voice_channel in ctx.guild.voice_channels:
                    voice_client: discord.VoiceClient = await voice_channel.connect()
                    await ctx.send(f"Connected to **\"{voice_channel.name}\"** (the nearest voice channel)!")
                    break
        else:
            if author_voicestate:
                if voice_client.channel != author_voicestate.channel:
                    await voice_client.move_to(author_voicestate.channel)
                    await ctx.send(f"Moved to **\"{author_voicestate.channel.name}\"** (your voice channel)!")
                else:
                    await ctx.send(f"I'm already in **\"{author_voicestate.channel.name}\"** (your voice channel)!")

    @commands.command()
    async def leave(self, ctx: commands.Context):
        """Leaves a voice channel"""
        voice_client: discord.VoiceClient = ctx.voice_client

        if voice_client:
            await voice_client.disconnect()
            await ctx.send(f"Disconnected from **\"{voice_client.channel.name}\"**!")
        else:
            await ctx.send("No voice channel to disconnect from...")

    @commands.command()
    async def play(self, ctx: commands.Context, *, search_or_url: str = ""):
        """Plays a track (overrides current track)"""
        # TODO https://stackoverflow.com/a/62360149/7688278
        # Allow links to play from specified timestamps
        voice_client: discord.VoiceClient = ctx.voice_client

        if not voice_client:
            return await ctx.send("I'm not in a voice channel!")

        if len(search_or_url) == 0:
            # test a random url while in development
            url = random.choice(self.bot.testing['vc']['yt-suggestions'])
        else:
            # assuming it's always an url for now
            url = re.findall(URL_PATTERN, search_or_url)[0]

        stream = await YTDLSource.from_url(url, loop=self.bot.loop)

        try:
            voice_client.play(stream, after=lambda e: print("Stream error.") if e else None)
        except discord.ClientException as e:
            print(e)
            await ctx.send("Can't play!")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stops the current track"""
        voice_client: discord.VoiceClient = ctx.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.stop()

    @commands.command()
    async def echo(self, ctx: commands.Context):
        """Echoes sound"""

    @commands.command()
    async def test(self, ctx: commands.Context):
        """Music test"""

        # join a voice channel
        await ctx.invoke(self.bot.get_command('join'))

        source = discord.FFmpegPCMAudio(os.path.join(self.bot.SOURCE_DIR, 'assets', self.bot.testing['vc']['music-file']))
        voice_client: discord.VoiceClient = ctx.voice_client

        print("playing music now!")
        if voice_client.is_playing():
            print("stopping music...")
            voice_client.stop()

        print("playing...")
        voice_client.play(source, after=lambda e: print("Done playing sound file.", e))


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Music(bot))
