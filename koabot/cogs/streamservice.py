"""Commands for streaming services like Twitch and Picarto"""
import random
import re

import discord
from discord.ext import commands

import koabot.utils


class StreamService(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='twitch')
    async def search_twitch(self, ctx, *args):
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

            if len(args) == 2:
                item = args[1]
                if re.findall(r'(^[0-9]+$)', item):
                    # is searching an id
                    search_type = 'user_id'
                else:
                    # searching an username
                    search_type = 'user_login'

                stream = await koabot.utils.net.http_request('https://api.twitch.tv/helix/streams?%s=%s' % (search_type, item), headers=self.bot.assets['twitch']['headers'], json=True)

                for strem in stream['data'][:3]:
                    await ctx.send('https://twitch.tv/%s' % strem['user_name'])

            else:
                streams = await koabot.utils.net.http_request('https://api.twitch.tv/helix/streams', headers=self.bot.assets['twitch']['headers'], json=True)

                for stream in streams['data'][:5]:
                    embed.description += 'stream "%s"\nstreamer %s (%s)\n\n' % (stream['title'], stream['user_name'], stream['user_id'])

                await ctx.send(embed=embed)

    async def get_picarto_stream_preview(self, msg, url: str):
        """Automatically fetch a preview of the running stream"""

        channel = msg.channel
        post_id = koabot.utils.posts.get_post_id(url, '.tv/', '?')

        if not post_id:
            return

        picarto_request = await koabot.utils.net.http_request('https://api.picarto.tv/v1/channel/name/' + post_id, json=True)

        if not picarto_request:
            await channel.send(random.choice(self.bot.quotes['stream_preview_failed']))
            return

        if not picarto_request['online']:
            await channel.send(random.choice(self.bot.quotes['stream_preview_offline']))
            return

        image = await koabot.utils.net.fetch_image(picarto_request['thumbnails']['web'])
        filename = koabot.utils.net.get_url_filename(picarto_request['thumbnails']['web'])

        embed = discord.Embed()
        embed.set_author(
            name=post_id,
            url='https://picarto.tv/' + post_id,
            icon_url=picarto_request['avatar'])
        embed.description = '**%s**' % picarto_request['title']
        embed.set_image(url='attachment://' + filename)
        embed.set_footer(
            text=self.bot.assets['picarto']['name'],
            icon_url=self.bot.assets['picarto']['favicon'])
        await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)
        return True


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(StreamService(bot))