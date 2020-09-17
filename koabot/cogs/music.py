"""Music functions!"""
import os

import discord
from discord.ext import commands

from koabot.koakuma import SOURCE_DIR


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx):
        pass

    @commands.command()
    async def leave(self, ctx):
        pass

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

        voice_client = ctx.voice_client
        author_voice_channel = ctx.author.voice.channel
        source = discord.FFmpegPCMAudio(os.path.join(SOURCE_DIR, 'assets', self.bot.testing['vc']['music-file']))

        if not voice_client:
            print('client doesn\'t exist!')
            if author_voice_channel:
                print('connecting to author\'s voice channel!')
                voice_client = await author_voice_channel.connect()
            else:
                print('searching for a voice channel...')
                if not ctx.guild.voice_channels:
                    print('No voice channels in this server.')
                    return

                for voice_channel in ctx.guild.voice_channels:
                    print('connecting to one...!')
                    voice_client = await voice_channel.connect()
        else:
            print('client exists!')
            if author_voice_channel:
                print('moving!')
                await voice_client.move_to(author_voice_channel)

        print('playing music now!')
        if voice_client.is_playing():
            print('stopping music...')
            voice_client.stop()

        print('playing...')
        voice_client.play(source, after=lambda e: print('Done playing sound file.', e))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Music(bot))
