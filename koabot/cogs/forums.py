"""Handle looking at posts from forum sites"""
import html
import itertools
import random

import basc_py4chan
import discord
from discord.ext import commands


class Forums(commands.Cog):
    """Forums class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='4chan', aliases=['4c', '4ch'])
    async def get_4chan_posts(self, ctx, user_board: str = 'u', thread_id: int = 0):
        """Get posts from a specific board, mostly those with pictures"""

        board = basc_py4chan.Board(user_board, https=True)
        if thread_id:
            thread = board.get_thread(thread_id)
            max_posts = 5

            if not thread:
                await ctx.send(random.choice(self.bot.quotes['thread_missing']))
                return

            posts_ready = []
            for post in thread.posts:
                embed = discord.Embed()

                if len(posts_ready) == 0:
                    if thread.topic.subject:
                        embed.title = html.unescape(thread.topic.subject)
                    else:
                        embed.title = '/%s/ thread' % user_board
                    embed.url = thread.topic.url

                embed.set_author(
                    name='%s @ %s' % (post.name, post.datetime),
                    url=post.semantic_url)
                embed.add_field(name='No.%s' % post.post_id, value='\u200b')
                embed.description = post.text_comment

                if post.has_file:
                    embed.set_image(url=post.file_url)

                posts_ready.append(embed)

                if len(posts_ready) >= max_posts:
                    break

            if len(posts_ready) > 0:
                posts_ready[len(posts_ready) - 1].set_footer(
                    text=self.bot.assets['4chan']['name'],
                    icon_url=self.bot.assets['4chan']['favicon'])

            for post in posts_ready:
                await ctx.send(embed=post)
        else:
            threads = board.get_threads()
            max_threads = 2
            max_posts_per_thread = 2

            threads_ready = []
            for thread in threads:
                if thread.sticky:
                    continue

                posts_ready = []
                fallback_post = None
                for post in thread.posts:
                    if post.has_file:
                        embed = discord.Embed()

                        if len(posts_ready) == 0:
                            if thread.topic.subject:
                                embed.title = html.unescape(thread.topic.subject)
                            else:
                                embed.title = '/%s/ thread' % user_board

                            embed.url = thread.topic.url

                        embed.set_author(
                            name='%s @ %s' % (post.name, post.datetime),
                            url=post.semantic_url)
                        embed.add_field(name='No.%s' % post.post_id, value='\u200b')
                        embed.description = post.text_comment
                        embed.set_image(url=post.file_url)
                        posts_ready.append(embed)

                        if len(posts_ready) >= max_posts_per_thread:
                            break
                    elif not fallback_post:
                        fallback_post = post

                if len(posts_ready) > 0:
                    if len(posts_ready) < max_posts_per_thread and fallback_post:
                        embed = discord.Embed()
                        embed.set_author(
                            name='%s @ %s' % (fallback_post.name, fallback_post.datetime),
                            url=fallback_post.semantic_url)
                        embed.add_field(name='No.%s' % fallback_post.post_id, value='\u200b')
                        embed.description = fallback_post.text_comment
                        posts_ready.append(embed)

                    posts_ready[len(posts_ready) - 1].set_footer(
                        text=self.bot.assets['4chan']['name'],
                        icon_url=self.bot.assets['4chan']['favicon'])
                    threads_ready.append(posts_ready)

                if len(threads_ready) >= max_threads:
                    break

            for post in list(itertools.chain.from_iterable(threads_ready)):
                if post.image.url:
                    print(post.author.url + '\n' + post.image.url + '\n\n')
                else:
                    print(post.author.url + '\nNo image\n\n')

                await ctx.send(embed=post)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Forums(bot))
