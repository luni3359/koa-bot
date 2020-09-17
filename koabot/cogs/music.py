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
        """Joins a voice channel"""
        voice_client = ctx.voice_client
        author_voicestate = ctx.author.voice

        if not voice_client:
            if author_voicestate:
                voice_client = await author_voicestate.channel.connect()
                await ctx.send(f'Connected to **"{author_voicestate.channel.name}"** (your voice channel)!')
            else:
                if not ctx.guild.voice_channels:
                    await ctx.send('There\'s no voice channels in this server...')
                    return

                for voice_channel in ctx.guild.voice_channels:
                    voice_client = await voice_channel.connect()
                    await ctx.send(f'Connected to **"{voice_channel.name}"** (the nearest voice channel)!')
        else:
            if author_voicestate:
                await voice_client.move_to(author_voicestate.channel)
                await ctx.send(f'Moved to **"{author_voicestate.channel.name}"** (your voice channel)!')

    @commands.command()
    async def leave(self, ctx):
        """Leaves a voice channel"""
        voice_client = ctx.voice_client

        if voice_client:
            await voice_client.disconnect()
            await ctx.send(f'Disconnected from **"{voice_client.channel.name}"**!')
        else:
            await ctx.send('No voice channel to disconnect from...')

    @commands.command()
    async def play(self, ctx):
        pass

    @commands.command()
    async def stop(self, ctx):
        """Stops the current track"""
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.stop()

    @commands.command()
    async def echo(self, ctx):
        pass

    @commands.command()
    async def test(self, ctx):
        """Music test"""

        # join a voice channel
        await ctx.invoke(self.bot.get_command('join'))

        source = discord.FFmpegPCMAudio(os.path.join(SOURCE_DIR, 'assets', self.bot.testing['vc']['music-file']))
        voice_client = ctx.voice_client

        print('playing music now!')
        if voice_client.is_playing():
            print('stopping music...')
            voice_client.stop()

        print('playing...')
        voice_client.play(source, after=lambda e: print('Done playing sound file.', e))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Music(bot))
