"""Search and gallery operations for art websites"""
from discord.ext import commands


class ImageBoard(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='danbooru', aliases=['dan'])
    async def search_danbooru(self, ctx, *tags):
        """Search on danbooru!"""
        board_cog = self.bot.get_cog('Board')

        if board_cog is None:
            print('BOARD COG WAS MISSING!')
            return

        await board_cog.search_board(ctx, tags)

    @commands.command(name='e621', aliases=['e6'])
    async def search_e621(self, ctx, *tags):
        """Search on e621!"""
        board_cog = self.bot.get_cog('Board')

        if board_cog is None:
            print('BOARD COG WAS MISSING!')
            return

        await board_cog.search_board(ctx, tags, board='e621')


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(ImageBoard(bot))
