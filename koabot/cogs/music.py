"""Music functions!"""
import os

import discord
from discord.ext import commands

from koabot.koakuma import SOURCE_DIR


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        """Mic test"""

        source = discord.FFmpegPCMAudio(os.path.join(SOURCE_DIR, 'assets', self.bot.testing['vc']['music-file']))

        if not ctx.voice_client:
            if ctx.guild.voice_channels:
                for voice_channel in ctx.guild.voice_channels:
                    try:
                        vc = await voice_channel.connect()
                        break
                    except discord.ClientException:
                        print('Already connected to a voice channel')
                        continue

        else:
            vc = ctx.voice_client

        if not vc:
            return

        if vc.is_playing():
            vc.stop()

        vc.play(source, after=lambda e: print('done', e))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Music(bot))
