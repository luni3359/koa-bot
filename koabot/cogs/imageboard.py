"""Search and gallery operations for art websites"""
import discord
from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.cogs.handler.gallery import Gallery
from koabot.cogs.site.deviantart import SiteDeviantArt
from koabot.cogs.site.imgur import SiteImgur
from koabot.cogs.site.patreon import SitePatreon
from koabot.cogs.site.pixiv import SitePixiv
from koabot.cogs.site.reddit import SiteReddit
from koabot.cogs.site.twitter import SiteTwitter
from koabot.kbot import KBot


class ImageBoard(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def gallery(self) -> Gallery:
        return self.bot.get_cog('Gallery')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def twitter(self) -> SiteTwitter:
        return self.bot.get_cog('SiteTwitter')

    @property
    def patreon(self) -> SitePatreon:
        return self.bot.get_cog('SitePatreon')

    @property
    def pixiv(self) -> SitePixiv:
        return self.bot.get_cog('SitePixiv')

    @property
    def imgur(self) -> SiteImgur:
        return self.bot.get_cog('SiteImgur')

    @property
    def deviantart(self) -> SiteDeviantArt:
        return self.bot.get_cog('SiteDeviantArt')

    @property
    def reddit(self) -> SiteReddit:
        return self.bot.get_cog('SiteReddit')

    @commands.command(name='danbooru', aliases=['dan'])
    async def search_danbooru(self, ctx, *, tags: str):
        """Search on danbooru!"""
        await self.board.search_board(ctx, tags, guide=self.bot.guides['gallery']['danbooru-default'])

    @commands.command(name='e621', aliases=['e6'])
    async def search_e621(self, ctx, *, tags: str):
        """Search on e621!"""
        await self.board.search_board(ctx, tags, board='e621', guide=self.bot.guides['gallery']['e621-default'])

    # Might as well use pixiv
    @commands.command(name='sankaku', enabled=False)
    async def search_sankaku(self, ctx, *, tags: str):
        """Search on sankaku!"""
        await self.board.search_board(ctx, tags, board='sankaku', guide=self.bot.guides['gallery']['sankaku-show'], hide_posts_remaining=True)

    async def show_gallery(self, msg: discord.Message, url: str, /, *, board: str, guide: dict, only_missing_preview: bool = False):
        """Show a gallery"""
        match board:
            case 'danbooru':
                await self.gallery.display_static(msg.channel, url, guide=guide, only_missing_preview=only_missing_preview)
            case 'e621':
                await self.gallery.display_static(msg.channel, url, board='e621', guide=guide, only_missing_preview=only_missing_preview)
            case 'twitter':
                await self.twitter.get_twitter_gallery(msg, url, guide=guide)
            case 'pixiv':
                await self.pixiv.get_pixiv_gallery(msg, url, only_missing_preview=only_missing_preview)
            case 'sankaku':
                await self.gallery.display_static(msg.channel, url, board='sankaku', guide=guide, only_missing_preview=only_missing_preview)
            case 'deviantart':
                await self.deviantart.get_deviantart_post(msg, url)
            case 'imgur':
                await self.imgur.get_imgur_gallery(msg, url)
            case 'reddit':
                await self.reddit.get_reddit_gallery(msg, url, guide=guide)
            case 'patreon':
                await self.patreon.get_patreon_gallery(msg, url)
            case _:
                raise ValueError(f'Board "{board}" has no gallery entry.')

    async def show_combined_gallery(self, msg: discord.Message, urls: list[str], /, *, board: str, guide: dict, only_missing_preview: bool = False):
        """Show multiple galleries that share one common element as one"""
        match board:
            case 'deviantart':
                await self.deviantart.get_deviantart_posts(msg, urls)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(self.botstatus.get_quote('board_blank_search'))


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(ImageBoard(bot))
