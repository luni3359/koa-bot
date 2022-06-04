"""Get user information"""
from dataclasses import dataclass

import discord
from dataclass_wizard import fromlist, json_field
from discord.ext import commands

import koabot.core.net as net_core
from koabot.kbot import KBot


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @commands.hybrid_command(aliases=['ava'])
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

    @commands.hybrid_command()
    async def inspire(self, ctx: commands.Context):
        """Get a random inspirational quote"""
        # Thanks for the idea freecodecamp!

        if not (api_response := (await net_core.http_request("https://zenquotes.io/api/random", json=True)).json):
            return await ctx.reply("I cannot channel those energies at the moment..."
                                   " Please try again later", mention_author=False)

        quote = fromlist(Quote, api_response)[0]
        await ctx.reply(f">>> \"{quote.quote}\"\nー *{quote.author}*", mention_author=False)


@dataclass
class Quote():
    quote: str = json_field("q")
    author: str = json_field("a")
    html: str = json_field("h")


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(UserActions(bot))
