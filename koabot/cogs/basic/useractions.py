"""Get user information"""
import discord
from discord.ext import commands

from koabot.kbot import KBot


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: KBot):
        self.bot = bot

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx: commands.Context):
        """Display an user's avatar"""

        if ctx.message.mentions:
            embeds: list[discord.Embed] = []
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


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(UserActions(bot))
