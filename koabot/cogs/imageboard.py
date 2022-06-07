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

    @commands.hybrid_command(name='danbooru', aliases=['dan'])
    async def search_danbooru(self, ctx: commands.Context, *, tags: str):
        """Search anime art on danbooru!"""
        if ctx.channel.is_nsfw:
            guide = self.bot.guides['gallery']['danbooru-default']
        else:
            guide = self.bot.guides['gallery']['donmai-safe']
        await self.board.search_board(ctx, tags, guide=guide)

    @commands.hybrid_command(name='donmai')
    async def search_donmai(self, ctx, *, tags: str):
        """Search family-friendly art on donmai!"""
        await self.board.search_board(ctx, tags, guide=self.bot.guides['gallery']['donmai-safe'])

    @commands.hybrid_command(name='e621', aliases=['e6'])
    async def search_e621(self, ctx: commands.Context, *, tags: str):
        """Search on e621!"""
        if ctx.channel.is_nsfw:
            guide = self.bot.guides['gallery']['e621-default']
        else:
            guide = self.bot.guides['gallery']['e621-safe']
        await self.board.search_board(ctx, tags, board='e621', guide=guide)

    async def show_preview(self, msg: discord.Message, url: str, /, *, board: str, guide: dict, only_if_missing: bool = False):
        """Show a preview"""
        match board:
            case 'danbooru':
                await self.gallery.display_static(msg.channel, url, guide=guide, only_if_missing=only_if_missing)
            case 'e621':
                await self.gallery.display_static(msg.channel, url, board='e621', guide=guide, only_if_missing=only_if_missing)
            case 'twitter':
                await self.twitter.get_twitter_gallery(msg, url, guide=guide)
            case 'pixiv':
                await self.pixiv.get_pixiv_gallery(msg, url, only_if_missing=only_if_missing)
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

    async def show_combined_preview(self, msg: discord.Message, urls: list[str], /, *, board: str, guide: dict, only_if_missing: bool = False):
        """Show multiple previews that share one common element as one"""
        match board:
            case 'deviantart':
                await self.deviantart.get_deviantart_posts(msg, urls)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(self.botstatus.get_quote('board_blank_search'))


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(ImageBoard(bot))
