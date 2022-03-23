"""Get user information"""

from typing import List

import discord
from discord.ext import commands
from discord.ext.commands.errors import (ExtensionAlreadyLoaded,
                                         ExtensionNotLoaded)


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx: commands.Context):
        """Display an user's avatar"""

        if ctx.message.mentions:
            embeds: List[discord.Embed] = []
            for mention in ctx.message.mentions:
                embed = discord.Embed()
                embed.set_image(url=mention.avatar.url)
                embed.set_author(
                    name=f'{mention.name} #{mention.discriminator}',
                    icon_url=mention.avatar.url)
                embeds.append(embed)
            await ctx.send(embeds=embeds)
        else:
            embed = discord.Embed()
            embed.set_image(url=ctx.message.author.avatar.url)
            embed.set_author(
                name=f'{ctx.message.author.name} #{ctx.message.author.discriminator}',
                icon_url=ctx.message.author.avatar.url)
            await ctx.send(embed=embed)

    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def _reload(self, ctx: commands.Context, *, module: str):
        """Reloads a module"""
        if module == "all":
            pass

        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f"{type(e).__name__}: {e}")
        else:
            await ctx.send(f"Successfully reloaded '{module}'.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def autoreload(self, ctx: commands.Context, mode: str):
        target = 'koabot.cogs.livereload'

        try:
            if mode == "on":
                self.bot.load_extension(target)
            elif mode == "off":
                self.bot.unload_extension(target)
        except ExtensionAlreadyLoaded:
            print("Autoreload is already on.")
        except ExtensionNotLoaded:
            print("Autoreload is already off.")


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
