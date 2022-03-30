"""Handles the management of imageboards"""
import re

import aiohttp
import commentjson
import discord
from discord.ext import commands

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.core.base import list_contains
from koabot.kbot import KBot


class Board(commands.Cog):
    """Board class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

        self._danbooru_auth: aiohttp.BasicAuth = None
        self._e621_auth: aiohttp.BasicAuth = None

    @property
    def danbooru_auth(self) -> aiohttp.BasicAuth:
        if not self._danbooru_auth:
            dan_keys = self.bot.auth_keys['danbooru']
            self._danbooru_auth = aiohttp.BasicAuth(login=dan_keys['username'], password=dan_keys['key'])

        return self._danbooru_auth

    @property
    def e621_auth(self) -> aiohttp.BasicAuth:
        if not self._e621_auth:
            e6_keys = self.bot.auth_keys['e621']
            self._e621_auth = aiohttp.BasicAuth(login=e6_keys['username'], password=e6_keys['key'])

        return self._e621_auth

    async def search_board(self, ctx: commands.Context, tags: str, /,  *, board: str = 'danbooru', guide: dict, hide_posts_remaining: bool = False) -> None:
        """Search on image boards!
        Arguments:
            ctx::comands.Context
                The context to interact with the discord API
            tags::str
                A string of the tags that have been sent by the user
        Keywords:
            board::str
                The board to manage. Default is 'danbooru'
            guide::dict
                The data which holds the board information
            hide_posts_remaining::bool
                Omit the final remaining count on the final post. False by default.
        """
        on_nsfw_channel = ctx.channel.is_nsfw()

        print(f'User searching for: {tags}')

        posts = None
        async with ctx.typing():
            try:
                posts = (await self.search_query(board=board, guide=guide, tags=tags, random=True, include_nsfw=on_nsfw_channel)).json
            except aiohttp.TooManyRedirects as e:
                return print("There's too many redirects: ", e)

        if not posts:
            return await ctx.send('Sorry, nothing found!')

        if 'posts' in posts:
            posts = posts['posts']

        # if the query is weird, ids won't appear in the results
        if 'id' not in posts[0]:
            return await ctx.send('Sorry, nothing found!')

        await self.send_posts(ctx, posts[:3], board=board, guide=guide, hide_posts_remaining=hide_posts_remaining)

    async def search_query(self, *, board: str = 'danbooru', guide: dict, **kwargs):
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
        post_id = kwargs.get('post_id')
        tags = kwargs.get('tags')
        limit = kwargs.get('limit', 0)
        random = kwargs.get('random', False)
        include_nsfw = kwargs.get('include_nsfw', False)

        data_arg = {
            'tags': tags
        }

        if random:
            data_arg['random'] = random

        if limit and limit > 0:
            data_arg['limit'] = limit

        match board:
            case 'danbooru':
                if post_id:
                    url = guide['api']['id_search_url'].format(post_id)
                    return await net_core.http_request(url, auth=self.danbooru_auth, json=True, err_msg=f'error fetching post #{post_id}')
                elif tags:
                    if include_nsfw:
                        url = 'https://danbooru.donmai.us'
                    else:
                        url = 'https://safebooru.donmai.us'

                    return await net_core.http_request(f'{url}/posts.json', auth=self.danbooru_auth, data=commentjson.dumps(data_arg), headers={'Content-Type': 'application/json'}, json=True, err_msg=f'error fetching search: {tags}')
            case 'e621':
                # e621 requires to know the User-Agent
                headers = guide['api']['headers']

                if post_id:
                    url = guide['api']['id_search_url'].format(post_id)
                    return await net_core.http_request(url, auth=self.e621_auth, json=True, headers=headers, err_msg=f'error fetching post #{post_id}')
                elif tags:
                    if include_nsfw:
                        url = 'https://e621.net'
                    else:
                        url = 'https://e926.net'

                    headers['Content-Type'] = 'application/json'
                    return await net_core.http_request(f'{url}/posts.json', auth=self.e621_auth, data=commentjson.dumps(data_arg), headers=headers, json=True, err_msg=f'error fetching search: {tags}')
            case 'sankaku':
                if post_id:
                    url = guide['api']['id_search_url'].format(post_id)
                    return await net_core.http_request(url, json=True, err_msg=f'error fetching post #{post_id}')
                elif tags:
                    search_query = '+'.join(tags.split(' '))
                    url = guide['api']['tag_search_url'].format(search_query)
                    return await net_core.http_request(url, json=True, err_msg=f'error fetching search: {tags}')
            case _:
                raise ValueError(f"Board \"{board}\" can't be handled by the post searcher.")

    async def send_posts(self, ctx: commands.Context, posts, /, *, board: str = 'danbooru', guide: dict, show_nsfw: bool = True, max_posts: int = 4, hide_posts_remaining: bool = False) -> None:
        """Handle sending posts retrieved from image boards
        Arguments:
            ctx
                The context to interact with the discord API
            posts::list | dict (json)
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
        if not isinstance(posts, list):
            posts = [posts]

        total_posts = len(posts)
        posts_processed = 0
        last_post = False

        if max_posts > 0:
            posts = posts[:max_posts]

        print(f'Sending {board} posts')

        for post in posts:
            posts_processed += 1
            post_id = post['id']
            print(f"Parsing post #{post_id} ({posts_processed}/{min(total_posts, max_posts)})...")

            embed = self.generate_embed(post, board=board, guide=guide)

            # if there's no image file or image url, send a link
            if not embed.image.url:
                await ctx.send(embed.url)
                continue

            if max_posts > 0:
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

            if not show_nsfw and post['rating'] != 's':
                if 'nsfw_placeholder' in self.bot.assets[board]:
                    embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
                else:
                    embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

                await ctx.send(f'<{embed.url}>', embed=embed)
            else:
                match board:
                    case 'danbooru':
                        if self.post_is_missing_preview(post, board=board) or last_post:
                            await ctx.send(f'<{embed.url}>', embed=embed)
                        else:
                            await ctx.send(embed.url)
                    case 'e621' | 'sankaku':
                        await ctx.send(f'<{embed.url}>', embed=embed)
                    case _:
                        raise ValueError('Board embed send not configured.')

            print(f'Post #{post_id} complete')

    def generate_embed(self, post, /, *, board: str = 'danbooru', guide: dict):
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
        embed = discord.Embed()

        post_id = post['id']

        match board:
            case 'danbooru':
                post_char = re.sub(r' \(.*?\)', '', post_core.combine_tags(post['tag_string_character']))
                post_copy = post_core.combine_tags(post['tag_string_copyright'], maximum=1)
                post_artist = post_core.combine_tags(post['tag_string_artist'])
                embed_post_title = ""

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
                    embed_post_title = embed_post_title[:self.bot.assets['danbooru']
                                                        ['max_embed_title_length'] - 3] + '...'

                embed.title = embed_post_title
            case 'e621':
                embed.title = f"#{post_id}: {post_core.combine_tags(post['tags']['artist'])} - e621"
            case 'sankaku':
                embed.title = f"Post {post_id}"
            case _:
                raise ValueError('Board embed title not configured.')

        embed.url = guide['post']['url'].format(post_id)

        if 'failed_post_preview' in self.bot.assets[board]:
            fileurl = self.bot.assets[board]['failed_post_preview']
        else:
            fileurl = self.bot.assets['default']['failed_post_preview']

        valid_res_keys = [res_key for res_key in guide['post']['resolutions'] if res_key in post]
        for res_key in valid_res_keys:
            match board:
                case 'e621':
                    url_candidate = post[res_key]['url']
                case _:
                    url_candidate = post[res_key]

            if net_core.get_url_fileext(url_candidate) in ['png', 'jpg', 'webp', 'gif']:
                fileurl = url_candidate
                break

        return embed.set_image(url=fileurl)

    def post_is_missing_preview(self, post, /, *, board: str = 'danbooru') -> bool:
        """Determine whether or not a post is missing its preview
        Arguments:
            post::json object

        Keywords:
            board::str
                The board to check the rules with. Default is 'danbooru'
        """
        match board:
            case 'e621':
                return list_contains(post['tags']['general'], self.bot.rules['no_preview_tags'][board]) and post['rating'] != 's'
            case 'sankaku':
                return True
            case _:
                return list_contains(post['tag_string_general'].split(), self.bot.rules['no_preview_tags'][board]) or post['is_banned']


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Board(bot))
