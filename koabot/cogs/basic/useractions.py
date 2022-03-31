"""Get user information"""
import discord
from discord.ext import commands

from koabot.kbot import KBot


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx: commands.Context):
        """Display an user's avatar"""
        embeds: list[discord.Embed] = []

        if ctx.message.mentions:
            requested_users = ctx.message.mentions
        else:
            requested_users = [ctx.message.author]

        for user in requested_users:
            embed = discord.Embed()
            embed.set_image(url=user.avatar.url)
            embed.set_author(
                name=f'{user.name} #{user.discriminator}',
                icon_url=user.avatar.url)
            embeds.append(embed)

        await ctx.send(embeds=embeds)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(UserActions(bot))
