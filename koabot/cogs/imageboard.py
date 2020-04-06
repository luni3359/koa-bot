from discord.ext import commands


class ImageBoard(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='danbooru', aliases=['dan'])
    async def danbooru(self, ctx, *tags, board='danbooru'):
        """Search danbooru"""

        board_cog = self.bot.get_cog('Board')
        if board_cog is None:
            return

        search = ' '.join(tags)
        print('User searching for: ' + search)

        on_nsfw_channel = ctx.channel.is_nsfw()

        async with ctx.typing():
            posts = await board_cog.search_query(board=board, tags=search, limit=3, random=True, include_nsfw=on_nsfw_channel)

        if not posts:
            await ctx.send('Sorry, nothing found!')
            return

        if 'posts' in posts:
            posts = posts['posts']

        await board_cog.send_posts(ctx, posts, board=board)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(ImageBoard(bot))
