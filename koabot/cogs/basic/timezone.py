"""Provide users a way to view timezones"""
import discord
from discord.ext import commands


class TimeZone(commands.Cog):
    """TimeZone class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['t'])
    async def time(self, ctx, *region_or_country):
        """Provide time zones"""
