"""Get user information"""
import discord
from discord.ext import commands

import koabot.core.net as net_core
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

    @commands.command()
    async def inspire(self, ctx: commands.Context):
        """Get a random inspirational quote"""
        # Thanks for the idea freecodecamp!

        if not (api_response := (await net_core.http_request("https://zenquotes.io/api/random", json=True)).json):
            return await ctx.send("I cannot channel those energies at the moment... Please try again later")

        quote, author, _ = api_response[0].values()
        await ctx.send(f">>> \"{quote}\"\nー *{author}*")


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(UserActions(bot))
