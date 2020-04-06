"""Handles the management of imageboards"""
import re
import typing

import commentjson
import discord
from discord.ext import commands

import koabot.utils


class Board(commands.Cog):
    """Board class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def search_query(self, **kwargs):
        """Handle searching in boards
        Keywords:
            board::str
                Specify what board to search on. Default is 'danbooru'
            post_id::int
                Used for searching by post id on a board
            tags::str
                Used for searching with tags on a board
            limit::int
                How many images to retrieve. Default is 0.
                Setting limit to 0 returns as many results as possible.
            random::bool
                Pick at random from results. Default is False
            include_nsfw::bool
                Whether or not the search will use safe versions of boards. Default is False

        Returns:
            json::dict
        """

        board = kwargs.get('board', 'danbooru')
        post_id = kwargs.get('post_id')
        tags = kwargs.get('tags')
        limit = kwargs.get('limit', 0)
        random_arg = kwargs.get('random', False)
        include_nsfw = kwargs.get('include_nsfw', False)

        data_arg = {
            'tags': tags,
            'random': random_arg
        }

        if limit and limit > 0:
            data_arg['limit'] = limit

        if board == 'danbooru':
            if post_id:
                url = 'https://danbooru.donmai.us/posts/%s.json' % post_id
                return await koabot.utils.net.http_request(url, auth=self.bot.danbooru_auth, json=True, err_msg='error fetching post #' + post_id)
            elif tags:
                if include_nsfw:
                    url = 'https://danbooru.donmai.us'
                else:
                    url = 'https://safebooru.donmai.us'

                return await koabot.utils.net.http_request(url + '/posts.json', auth=self.bot.danbooru_auth, data=commentjson.dumps(data_arg), headers={'Content-Type': 'application/json'}, json=True, err_msg='error fetching search: ' + tags)
        elif board == 'e621':
            # e621 requires to know the User-Agent
            headers = self.bot.assets['e621']['headers']

            if post_id:
                url = 'https://e621.net/posts/%s.json' % post_id
                return await koabot.utils.net.http_request(url, auth=self.bot.e621_auth, json=True, headers=headers, err_msg='error fetching post #' + post_id)
            elif tags:
                if include_nsfw:
                    url = 'https://e621.net'
                else:
                    url = 'https://e926.net'

                headers['Content-Type'] = 'application/json'
                return await koabot.utils.net.http_request(url + '/posts.json', auth=self.bot.e621_auth, data=commentjson.dumps(data_arg), headers=headers, json=True, err_msg='error fetching search: ' + tags)
        else:
            raise ValueError('Board "%s" can\'t be handled by the post searcher.' % board)

    async def send_posts(self, ctx, posts, **kwargs):
        """Handle sending posts retrieved from image boards
        Arguments:
            ctx
                The context to interact with the discord API
            posts::list or json object
                The post(s) to be sent to a channel

        Keywords:
            board::str
                The board to manage. Default is 'danbooru'
            show_nsfw::bool
                Whether or not nsfw posts should have their previews shown. Default is True
            max_posts::int
                How many posts should be shown before showing how many of them were cut-off.
                If max_posts is set to 0 then no footer will be shown and no posts will be omitted.
        """

        board = kwargs.get('board', 'danbooru')
        show_nsfw = kwargs.get('show_nsfw', True)
        max_posts = kwargs.get('max_posts', 4)

        if not isinstance(posts, typing.List):
            posts = [posts]

        total_posts = len(posts)
        posts_processed = 0
        last_post = False

        if max_posts != 0:
            posts = posts[:max_posts]

        print('Sending %s posts' % board)

        for post in posts:
            posts_processed += 1
            print('Parsing post #%i (%i/%i)...' % (post['id'], posts_processed, min(total_posts, max_posts)))

            denied_ext = ['webm']
            if 'file_ext' in post and post['file_ext'] in denied_ext:
                if board == 'danbooru':
                    url = 'https://danbooru.donmai.us/posts/%i' % post['id']
                elif board == 'e621':
                    url = 'https://e621.net/posts/%i' % post['id']

                await ctx.send(url)
                continue

            embed = self.generate_embed(post, board=board)

            if max_posts != 0:
                if posts_processed >= min(max_posts, total_posts):
                    last_post = True

                    if total_posts > max_posts:
                        embed.set_footer(
                            text='%i+ remaining' % (total_posts - max_posts),
                            icon_url=koabot.koakuma.bot.assets[board]['favicon']['size16'])
                    else:
                        embed.set_footer(
                            text=koabot.koakuma.bot.assets[board]['name'],
                            icon_url=koabot.koakuma.bot.assets[board]['favicon']['size16'])

            if not show_nsfw and post['rating'] is not 's':
                if 'nsfw_placeholder' in koabot.koakuma.bot.assets[board]:
                    embed.set_image(url=koabot.koakuma.bot.assets[board]['nsfw_placeholder'])
                else:
                    embed.set_image(url=koabot.koakuma.bot.assets['default']['nsfw_placeholder'])

                await ctx.send('<%s>' % embed.url, embed=embed)
            else:
                if board == 'danbooru':
                    if koabot.utils.posts.post_is_missing_preview(post, board=board) or last_post:
                        await ctx.send('<%s>' % embed.url, embed=embed)
                    else:
                        await ctx.send(embed.url)
                elif board == 'e621':
                    await ctx.send('<%s>' % embed.url, embed=embed)

            print('Post #%i complete' % post['id'])

    def generate_embed(self, post, **kwargs):
        """Generate embeds for image board post urls
        Arguments:
            post
                The post object

        Keywords:
            board::str
                The board to handle. Default is 'danbooru'
        """

        board = kwargs.get('board', 'danbooru')
        embed = discord.Embed()

        if board == 'danbooru':
            post_char = re.sub(r' \(.*?\)', '', koabot.utils.posts.combine_tags(post['tag_string_character']))
            post_copy = koabot.utils.posts.combine_tags(post['tag_string_copyright'])
            post_artist = koabot.utils.posts.combine_tags(post['tag_string_artist'])
            embed_post_title = ''

            if post_char:
                embed_post_title += post_char

            if post_copy:
                if not post_char:
                    embed_post_title += post_copy
                else:
                    embed_post_title += ' (%s)' % post_copy

            if post_artist:
                embed_post_title += ' drawn by ' + post_artist

            if not post_char and not post_copy and not post_artist:
                embed_post_title += '#%i' % post['id']

            embed_post_title += ' | Danbooru'
            if len(embed_post_title) >= koabot.koakuma.bot.assets['danbooru']['max_embed_title_length']:
                embed_post_title = embed_post_title[:koabot.koakuma.bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

            embed.title = embed_post_title
            embed.url = 'https://danbooru.donmai.us/posts/%i' % post['id']
        elif board == 'e621':
            embed.title = '#%s: %s - e621' % (post['id'], koabot.utils.posts.combine_tags(post['tags']['artist']))
            embed.url = 'https://e621.net/posts/%i' % post['id']

        if 'failed_post_preview' in koabot.koakuma.bot.assets[board]:
            fileurl = koabot.koakuma.bot.assets[board]['failed_post_preview']
        else:
            fileurl = koabot.koakuma.bot.assets['default']['failed_post_preview']

        valid_urls_keys = ['large_file_url', 'file_url', 'preview_file_url', 'sample', 'file', 'preview']
        for key in valid_urls_keys:
            if key in post:
                if board == 'e621':
                    fileurl = post[key]['url']
                else:
                    fileurl = post[key]
                break

        embed.set_image(url=fileurl)
        return embed


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Board(bot))
