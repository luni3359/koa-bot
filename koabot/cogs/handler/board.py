"""Handles the management of imageboards"""
import re
import typing

import aiohttp
import commentjson
import discord
from discord.ext import commands

import koabot.utils as utils
import koabot.utils.net
import koabot.utils.posts


class Board(commands.Cog):
    """Board class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.danbooru_auth = aiohttp.BasicAuth(login=self.bot.auth_keys['danbooru']['username'], password=self.bot.auth_keys['danbooru']['key'])
        self.e621_auth = aiohttp.BasicAuth(login=self.bot.auth_keys['e621']['username'], password=self.bot.auth_keys['e621']['key'])

    async def search_board(self, ctx, tags: typing.List, board='danbooru', **kwargs):
        """Search on image boards!
        Arguments:
            ctx
                The context to interact with the discord API
            tags::*args (list)
                List of the tags sent by the user
            board::str
                The board to manage. Default is 'danbooru'
        Keywords:
            guide::dict
                The data which holds the board information
            hide_posts_remaining::bool
                Omit the final remaining count on the final post. False by default.
        """

        guide = kwargs.get('guide', None)
        hide_posts_remaining = kwargs.get('hide_posts_remaining', False)

        if len(tags) == 0:
            await ctx.send('Please make a search.')
            return

        search = ' '.join(tags)
        print(f'User searching for: {search}')

        on_nsfw_channel = ctx.channel.is_nsfw()

        async with ctx.typing():
            posts = (await self.search_query(board=board, guide=guide, tags=search, limit=3, random=True, include_nsfw=on_nsfw_channel)).json

        if not posts:
            await ctx.send('Sorry, nothing found!')
            return

        if 'posts' in posts:
            posts = posts['posts']

        await self.send_posts(ctx, posts[:3], board=board, guide=guide, hide_posts_remaining=hide_posts_remaining)

    async def search_query(self, **kwargs):
        """Handle searching in boards
        Keywords:
            board::str
                Specify what board to search on. Default is 'danbooru'
            guide::dict
                The data which holds the board information
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
        guide = kwargs.get('guide', None)
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
                url = guide['api']['id_search_url'].format(post_id)
                return await utils.net.http_request(url, auth=self.danbooru_auth, json=True, err_msg=f'error fetching post #{post_id}')
            elif tags:
                if include_nsfw:
                    url = 'https://danbooru.donmai.us'
                else:
                    url = 'https://safebooru.donmai.us'

                return await utils.net.http_request(f'{url}/posts.json', auth=self.danbooru_auth, data=commentjson.dumps(data_arg), headers={'Content-Type': 'application/json'}, json=True, err_msg=f'error fetching search: {tags}')
        elif board == 'e621':
            # e621 requires to know the User-Agent
            headers = guide['api']['headers']

            if post_id:
                url = guide['api']['id_search_url'].format(post_id)
                return await utils.net.http_request(url, auth=self.e621_auth, json=True, headers=headers, err_msg=f'error fetching post #{post_id}')
            elif tags:
                if include_nsfw:
                    url = 'https://e621.net'
                else:
                    url = 'https://e926.net'

                headers['Content-Type'] = 'application/json'
                return await utils.net.http_request(f'{url}/posts.json', auth=self.e621_auth, data=commentjson.dumps(data_arg), headers=headers, json=True, err_msg=f'error fetching search: {tags}')
        elif board == 'sankaku':
            if post_id:
                url = guide['api']['id_search_url'].format(post_id)
                return await utils.net.http_request(url, json=True, err_msg=f'error fetching post #{post_id}')
            elif tags:
                search_query = '+'.join(tags.split(' '))
                url = guide['api']['tag_search_url'].format(search_query)
                return await utils.net.http_request(url, json=True, err_msg=f'error fetching search: {tags}')
        else:
            raise ValueError(f'Board "{board}" can\'t be handled by the post searcher.')

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
            guide::dict
                The data which holds the board information
            show_nsfw::bool
                Whether or not nsfw posts should have their previews shown. True by default.
            max_posts::int
                How many posts should be shown before showing how many of them were cut-off.
                If max_posts is set to 0 then no footer will be shown and no posts will be omitted.
            hide_posts_remaining::bool
                Omit the final remaining count on the final post. False by default.
        """

        board = kwargs.get('board', 'danbooru')
        guide = kwargs.get('guide', None)
        show_nsfw = kwargs.get('show_nsfw', True)
        max_posts = kwargs.get('max_posts', 4)
        hide_posts_remaining = kwargs.get('hide_posts_remaining', False)

        if not isinstance(posts, typing.List):
            posts = [posts]

        total_posts = len(posts)
        posts_processed = 0
        last_post = False

        if max_posts != 0:
            posts = posts[:max_posts]

        print(f'Sending {board} posts')

        for post in posts:
            posts_processed += 1
            post_id = post['id']
            print(f'Parsing post #{post_id} ({posts_processed}/{min(total_posts, max_posts)})...')

            embed = self.generate_embed(post, board=board, guide=guide)

            # if there's no image file or image url, send a link
            if not embed.image.url:
                await ctx.send(embed.url)
                continue

            if max_posts != 0:
                if posts_processed >= min(max_posts, total_posts):
                    last_post = True

                    if total_posts > max_posts and not hide_posts_remaining:
                        embed.set_footer(
                            text=f'{total_posts - max_posts}+ remaining',
                            icon_url=self.bot.assets[board]['favicon']['size16'])
                    else:
                        embed.set_footer(
                            text=guide['embed']['footer_text'],
                            icon_url=self.bot.assets[board]['favicon']['size16'])

            if not show_nsfw and post['rating'] is not 's':
                if 'nsfw_placeholder' in self.bot.assets[board]:
                    embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
                else:
                    embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

                await ctx.send(f'<{embed.url}>', embed=embed)
            else:
                if board == 'danbooru':
                    if utils.posts.post_is_missing_preview(post, board=board) or last_post:
                        await ctx.send(f'<{embed.url}>', embed=embed)
                    else:
                        await ctx.send(embed.url)
                elif board == 'e621' or board == 'sankaku':
                    await ctx.send(f'<{embed.url}>', embed=embed)
                else:
                    raise ValueError('Board embed send not configured.')

            print(f'Post #{post_id} complete')

    def generate_embed(self, post, **kwargs):
        """Generate embeds for image board post urls
        Arguments:
            post
                The post object

        Keywords:
            board::str
                The board to handle. Default is 'danbooru'
            guide::dict
                The data which holds the board information
        """

        board = kwargs.get('board', 'danbooru')
        guide = kwargs.get('guide', None)
        embed = discord.Embed()

        post_id = post['id']

        if board == 'danbooru':
            post_char = re.sub(r' \(.*?\)', '', utils.posts.combine_tags(post['tag_string_character']))
            post_copy = utils.posts.combine_tags(post['tag_string_copyright'])
            post_artist = utils.posts.combine_tags(post['tag_string_artist'])
            embed_post_title = ''

            if post_char:
                embed_post_title += post_char

            if post_copy:
                if not post_char:
                    embed_post_title += post_copy
                else:
                    embed_post_title += f' ({post_copy})'

            if post_artist:
                embed_post_title += f' drawn by {post_artist}'

            if not post_char and not post_copy and not post_artist:
                embed_post_title += f"#{post_id}"

            embed_post_title += ' | Danbooru'
            if len(embed_post_title) >= self.bot.assets['danbooru']['max_embed_title_length']:
                embed_post_title = embed_post_title[:self.bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

            embed.title = embed_post_title
        elif board == 'e621':
            embed.title = f"#{post_id}: {utils.posts.combine_tags(post['tags']['artist'])} - e621"
        elif board == 'sankaku':
            embed.title = f"Post {post_id}"
        else:
            raise ValueError('Board embed title not configured.')

        embed.url = self.bot.assets[board]['post_url'].format(post_id)

        if 'failed_post_preview' in self.bot.assets[board]:
            fileurl = self.bot.assets[board]['failed_post_preview']
        else:
            fileurl = self.bot.assets['default']['failed_post_preview']

        for res_key in guide['post']['resolutions']:
            if res_key in post:
                if board == 'e621':
                    url_candidate = post[res_key]['url']
                else:
                    url_candidate = post[res_key]

                if utils.net.get_url_fileext(url_candidate) in ['png', 'jpg', 'webp', 'gif']:
                    fileurl = url_candidate
                    break

        embed.set_image(url=fileurl)
        return embed


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Board(bot))
