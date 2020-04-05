from discord.ext import commands
from koabot.boards import boardcog


class Danbooru(boardcog.BaseBoard):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)


def setup(bot: commands.Bot):
    bot.add_cog(Danbooru(bot))
