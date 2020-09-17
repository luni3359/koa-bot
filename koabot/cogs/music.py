"""Music functions!"""
import os

import discord
from discord.ext import commands

from koabot.koakuma import SOURCE_DIR


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.source = discord.FFmpegPCMAudio(os.path.join(SOURCE_DIR, 'assets', self.bot.testing['vc']['music-file']))
        self.voice_client = None

    @commands.command()
    async def play(self, ctx):
        pass

    @commands.command()
    async def stop(self, ctx):
        pass

    @commands.command()
    async def echo(self, ctx):
        pass

    @commands.command()
    async def test(self, ctx):
        """Music test"""

        if not ctx.voice_client:
            if ctx.guild.voice_channels:
                for voice_channel in ctx.guild.voice_channels:
                    try:
                        voice_client = await voice_channel.connect()
                        break
                    except discord.ClientException:
                        print('Already connected to a voice channel')
                        continue
        else:
            voice_client = ctx.voice_client

        if not voice_client:
            return

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(self.source, after=lambda e: print('done', e))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Music(bot))
