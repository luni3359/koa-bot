"""Music functions!"""
import os
import random

import discord
import youtube_dl
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
                    break
        else:
            if author_voicestate:
                if voice_client.channel != author_voicestate.channel:
                    await voice_client.move_to(author_voicestate.channel)
                    await ctx.send(f'Moved to **"{author_voicestate.channel.name}"** (your voice channel)!')
                else:
                    await ctx.send(f'I\'m already in **"{author_voicestate.channel.name}"** (your voice channel)!')

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
    async def play(self, ctx, *search_or_url):
        """Plays a track (overrides current track)"""

        if len(search_or_url) == 0:
            await ctx.send('Please make a search or paste a link!')
            return

        voice_client = ctx.voice_client

        ydl_opts = {
            'format': 'bestaudio/best'
        }

        url = random.choice(self.bot.testing['vc']['yt-suggestions'])
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            track_info = ydl.extract_info(url, download=False)
            voice_client.play(discord.FFmpegPCMAudio(track_info['formats'][0]['url']))

    @commands.command()
    async def stop(self, ctx):
        """Stops the current track"""
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.stop()

    @commands.command()
    async def echo(self, ctx):
        """Echoes sound"""

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
