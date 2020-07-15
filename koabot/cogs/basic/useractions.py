"""Get user information"""
import discord
from discord.ext import commands


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx):
        """Display the avatar of an user"""

        if ctx.message.mentions:
            for mention in ctx.message.mentions:
                embed = discord.Embed()
                embed.set_image(url=mention.avatar_url)
                embed.set_author(
                    name=f'{mention.name} #{mention.discriminator}',
                    icon_url=mention.avatar_url)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed()
            embed.set_image(url=ctx.message.author.avatar_url)
            embed.set_author(
                name=f'{ctx.message.author.name} #{ctx.message.author.discriminator}',
                icon_url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
