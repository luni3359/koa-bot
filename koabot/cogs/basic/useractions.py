"""Get user information"""

import discord
from discord.ext import commands


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx: commands.Context):
        """Display an user's avatar"""

        if ctx.message.mentions:
            embeds = []
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


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
