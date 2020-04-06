import random

import discord
from discord.ext import commands

import koabot.utils


class StreamService(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
