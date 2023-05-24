"""Provide users a way to view timezones.
The !time command allows typing a region or a country to further displays time zones there.
"""
from datetime import datetime

import pytz
from discord.ext import commands

from koabot.kbot import KBot


class TimeZone(commands.Cog):
    """TimeZone class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @commands.hybrid_command(aliases=['t'])
    async def time(self, ctx: commands.Context, *, region_or_country: str = ""):
        """Provide time zones"""

        if not region_or_country:
            tzs = [
                ['USA', 'America/Chicago'],
                ['Canada', 'America/Toronto'],
                ['Japan', 'Asia/Tokyo'],
                ['Mexico', 'America/Mexico_City']
            ]

        tz_result: list[str] = ["```\n"]
        for label, timezone in tzs:
            tz = pytz.timezone(timezone)
            tz_time = datetime.now(tz)
            # https://strftime.org
            tz_result.append((f"{label}: ").ljust(8) + tz_time.strftime("%a, %b %d %H:%M:%S\n"))

        tz_result.append("```")

        await ctx.reply("".join(tz_result), mention_author=False)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(TimeZone(bot))
