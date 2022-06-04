"""Bot-related commands and features"""
import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from single_source import get_version

from koabot.kbot import KBot


class BotStatus(commands.Cog):
    """BotStatus class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @commands.hybrid_command()
    async def uptime(self, ctx: commands.Context, /):
        """Mention the current uptime"""

        delta_uptime: timedelta = datetime.utcnow() - self.bot.launch_time
        (hours, remainder) = divmod(int(delta_uptime.total_seconds()), 3600)
        (minutes, seconds) = divmod(remainder, 60)
        (days, hours) = divmod(hours, 24)
        await ctx.reply(f"I've been running for {days} days, {hours} hours, {minutes} minutes and {seconds} seconds.", mention_author=False)

    @commands.hybrid_command()
    async def version(self, ctx: commands.Context, /):
        """Show bot's version"""
        version = get_version(self.bot.PROJECT_NAME, self.bot.PROJECT_DIR)
        await ctx.reply(f"On version `{version}`.", mention_author=False)

    async def typing_a_message(self, ctx: commands.Context, /, **kwargs):
        """Make Koakuma seem alive with a 'is typing' delay

        Keywords:
            content::str
                Message to be said.
            embed::discord.Embed
                Self-explanatory. Default is None.
            rnd_duration::list | int
                A list with two int values of what's the least that should be waited for to the most, chosen at random.
                If provided an int the 0 will be assumed at the start.
            min_duration::int
                The amount of time that will be waited regardless of rnd_duration.
        """

        content: str = kwargs.get('content')
        embed: discord.Embed = kwargs.get('embed')
        rnd_duration: list | int = kwargs.get('rnd_duration')
        min_duration: int = kwargs.get('min_duration', 0)

        if isinstance(rnd_duration, int):
            rnd_duration = [0, rnd_duration]

        async with ctx.typing():
            if rnd_duration:
                time_to_wait = max(min_duration, random.randint(rnd_duration[0], rnd_duration[1]))
                await asyncio.sleep(time_to_wait)
            else:
                await asyncio.sleep(min_duration)

            if embed is not None:
                if content:
                    await ctx.send(content, embed=embed)
                else:
                    await ctx.send(embed=embed)
            else:
                await ctx.send(content)

    def get_quote(self, key: str, /, **kwargs) -> str:
        """Get a quote from Koakuma's file of things to say"""
        if kwargs:
            return random.choice(self.bot.quotes[key]).format(**kwargs)

        return random.choice(self.bot.quotes[key])


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(BotStatus(bot))
