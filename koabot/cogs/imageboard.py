"""Search and gallery operations for art websites"""
import discord
from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.cogs.handler.gallery import Gallery


class ImageBoard(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='danbooru', aliases=['dan'])
    async def search_danbooru(self, ctx, *, tags: str):
        """Search on danbooru!"""
        board_cog: Board = self.bot.get_cog('Board')
        await board_cog.search_board(ctx, tags, guide=self.bot.guides['gallery']['danbooru-default'])

    @commands.command(name='e621', aliases=['e6'])
    async def search_e621(self, ctx, *, tags: str):
        """Search on e621!"""
        board_cog: Board = self.bot.get_cog('Board')
        await board_cog.search_board(ctx, tags, board='e621', guide=self.bot.guides['gallery']['e621-default'])

    # Might as well use pixiv
    @commands.command(name='sankaku', enabled=False)
    async def search_sankaku(self, ctx, *, tags: str):
        """Search on sankaku!"""
        board_cog: Board = self.bot.get_cog('Board')
        await board_cog.search_board(ctx, tags, board='sankaku', guide=self.bot.guides['gallery']['sankaku-show'], hide_posts_remaining=True)

    async def show_gallery(self, msg: discord.Message, url: str, /, *, board: str, guide: dict, only_missing_preview: bool = False):
        """Show a gallery"""
        gallery_cog: Gallery = self.bot.get_cog('Gallery')

        if board == 'danbooru':
            await gallery_cog.display_static(msg.channel, url, guide=guide, only_missing_preview=only_missing_preview)
        elif board == 'e621':
            await gallery_cog.display_static(msg.channel, url, board='e621', guide=guide, only_missing_preview=only_missing_preview)
        elif board == 'twitter':
            await gallery_cog.get_twitter_gallery(msg, url)
        elif board == 'pixiv':
            await gallery_cog.get_pixiv_gallery(msg, url)
        elif board == 'sankaku':
            await gallery_cog.display_static(msg.channel, url, board='sankaku', guide=guide, only_missing_preview=only_missing_preview)
        elif board == 'deviantart':
            await gallery_cog.get_deviantart_post(msg, url)
        elif board == 'imgur':
            await gallery_cog.get_imgur_gallery(msg, url)
        elif board == 'reddit':
            await gallery_cog.get_reddit_gallery(msg, url, guide=guide)
        else:
            raise ValueError(f'Board "{board}" has no gallery entry.')

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            bot_cog: BotStatus = self.bot.get_cog('BotStatus')
            return await ctx.send(bot_cog.get_quote('board_blank_search'))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(ImageBoard(bot))
