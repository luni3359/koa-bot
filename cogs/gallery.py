from discord.ext import commands


class GalleryCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(invoke_without_command=True, hidden=True)
    @commands.is_owner()
    async def omg(self, ctx):
        print(ctx)
        await ctx.send('This works...?!')

    @commands.command()
    async def ohwat(self, ctx):
        await ctx.send('For no special reason.')


def setup(bot):
    bot.add_cog(GalleryCog(bot))
