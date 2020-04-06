"""Handles management of galleries"""
from discord.ext import commands


class Gallery(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_board_gallery(self):
        pass

    async def search_in_board(self):
        pass

    async def send_board_posts(self):
        pass

    def generate_board_embed(self):
        pass

    def post_is_missing_preview(self):
        pass

    def get_post_id(self):
        pass


def setup(bot: commands.Bot):
    bot.add_cog(Gallery(bot))
