import discord
from discord.ext import commands
from mediawiki import MediaWiki
from mediawiki import exceptions as MediaExceptions

import koabot.core.net as net_core
from koabot.cogs.infolookup import Dictionary
from koabot.core.utils import smart_truncate
from koabot.kbot import KBot


class SiteWikipedia(Dictionary):
    """Wikipedia operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.max_summary_length = 2000

        self._wikipedia: MediaWiki = None

    @property
    def wikipedia(self) -> MediaWiki:
        if not self._wikipedia:
            self._wikipedia = MediaWiki()

        return self._wikipedia

    async def search(self, ctx: commands.Context, search_term: str):
        guide = self.bot.guides['explanation']['wikipedia-default']

        page_results = self.wikipedia.search(search_term)
        page_title = []

        try:
            page_title = page_results[0]
        except IndexError:
            await ctx.send("I can't find anything relevant. Sorry...")
            return

        # TODO: Check out that new wikimedia feature!
        try:
            page = self.wikipedia.page(page_title, auto_suggest=False)
            embed = discord.Embed()
            embed.title = page.title
            embed.url = page.url

            js = (await net_core.http_request(f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}", json=True)).json
            if 'thumbnail' in js:
                embed.set_image(url=js['thumbnail']['source'])

            embed.description = smart_truncate(page.summary, self.max_summary_length)
            embed.set_footer(text=guide['embed']['footer_text'], icon_url=guide['embed']['favicon']['size16'])
            await ctx.send(embed=embed)
        except MediaExceptions.DisambiguationError as e:
            bot_msg = 'There are many definitions for that... do you see anything that matches?\n'

            for suggestion in e.options[:3]:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)
        except MediaExceptions.PageError:
            bot_msg = "Oh, I can't find anything like that... how about these?\n"
            suggestions = self.wikipedia.search(search_term, results=3)

            for suggestion in suggestions:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteWikipedia(bot))
