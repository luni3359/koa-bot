import discord

import koabot.core.posts as post_core
from koabot.core.site import Site
from koabot.kbot import KBot


class SitePatreon(Site):
    """Patreon operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)

    def get_id(self, url: str) -> str:
        return post_core.get_name_or_id(url, start='/posts/', pattern=r'[0-9]+$')

    async def get_patreon_gallery(self, msg: discord.Message, url: str):
        if not (post_id := self.get_id(url)):
            return


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SitePatreon(bot))
