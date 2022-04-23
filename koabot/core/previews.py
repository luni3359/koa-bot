from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.kbot import KBot


class SitePreview(commands.Cog):
    """Site preview"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SitePreview(bot))
