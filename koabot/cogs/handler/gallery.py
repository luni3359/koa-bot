"""Handles the use of imageboard galleries"""
import shutil
from pathlib import Path

import discord
import imagehash
from discord.ext import commands
from PIL import Image

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.kbot import KBot


class BooruParsedPost():
    def __init__(self, post_id, ext, filename, path) -> None:
        self.id: int = post_id
        self.ext = ext
        self.filename = filename
        self.path = path
        self.hash = []
        self.score = []


class Gallery(commands.Cog):
    """Gallery class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    async def display_static(self, channel: discord.TextChannel, url: str, /, *, board: str = 'danbooru', guide: dict, only_if_missing: bool = False) -> None:
        """Display posts from a gallery in separate unmodifiable embeds
        Arguments:
            channel::discord.TextChannel
                Channel the message is in
            url::str
                Url to get a gallery from
        Keywords:
            board::str
                Name of the board to handle. Default is 'danbooru'
            guide::dict
                The data which holds the board information
            only_if_missing::bool
                Only shows a preview if the native embed is missing from the original link. Default is False
        """
        if not guide:
            raise ValueError("The 'guide' keyword argument is not defined.")

        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end'] if 'id_end' in guide['post'] else ['?']
        pattern = guide['post']['pattern'] if 'pattern' in guide['post'] else ""

        if not (post_id := post_core.get_name_or_id(url, start=id_start, end=id_end, pattern=pattern)):
            return

        board_cog = self.board
        if not (post := (await board_cog.search_query(board=board, guide=guide, post_id=post_id)).json):
            return

        # e621 fix for broken API
        if 'post' in post:
            post = post['post']

        post_id = post['id']

        botstatus_cog = self.botstatus
        on_nsfw_channel = channel.is_nsfw()
        first_post_missing_preview = board_cog.post_is_missing_preview(post, board=board)
        posts = []

        if post['rating'] != 's' and not on_nsfw_channel:
            # Silently ignore
            return
            # embed = discord.Embed()
            # if 'nsfw_placeholder' in self.bot.assets[board]:
            #     embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
            # else:
            #     embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            # content = f"{msg.author.mention} {botstatus_cog.get_quote('improper_content_reminder')}"
            # await botstatus_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

        match board:
            case 'e621':
                has_children = post['relationships']['has_active_children']
                parent_id = post['relationships']['parent_id']
                c_search = f'parent:{post_id} order:id'
                p_search = [
                    f'id:{parent_id}',
                    f'parent:{parent_id} order:id -id:{post_id}'
                ]
            case _:
                has_children = post['has_children']
                parent_id = post['parent_id']
                c_search = f'parent:{post_id} order:id -id:{post_id}'
                p_search = f'parent:{parent_id} order:id -id:{post_id}'

        if only_if_missing:
            if first_post_missing_preview and (post['rating'] == 's' or on_nsfw_channel):
                await board_cog.send_posts(channel, post, board=board, guide=guide)
            return

        if has_children:
            search = c_search
        elif parent_id:
            search = p_search
        else:
            if first_post_missing_preview and (post['rating'] == 's' or on_nsfw_channel):
                await board_cog.send_posts(channel, post, board=board, guide=guide)
            return

        if isinstance(search, str):
            search = [search]

        for s in search:
            results = await board_cog.search_query(board=board, guide=guide, tags=s, include_nsfw=on_nsfw_channel)
            results = results.json

            # e621 fix for broken API
            if 'posts' in results:
                results = results['posts']

            posts.extend(results)

        # Rudimentary fix when NSFW results are returned and it's a safe channel (should actually revert at some point)
        # Ought to respect the choice to display posts anyway but without thumbnail
        nsfw_culled = False
        if not on_nsfw_channel:
            # filters all safe results into the posts variable
            total_posts_count = len(posts)
            posts = [post for post in posts if post['rating'] == 's']

            if len(posts) != total_posts_count:
                nsfw_culled = True

        parsed_posts: list[BooruParsedPost] = []
        if board == 'danbooru':
            file_cache_dir = Path(self.bot.CACHE_DIR, board, "files")
            file_cache_dir.mkdir(exist_ok=True)

            test_posts: list[dict] = [post]
            test_posts.extend(posts)

            for test_post in test_posts:
                should_cache = True
                for res_key in self.bot.assets[board]['post_quality']:
                    if res_key in test_post:
                        url_candidate = test_post[res_key]
                        file_ext = net_core.get_url_fileext(url_candidate)
                        if file_ext in ['png', 'jpg', 'webp']:
                            file_url = url_candidate
                            file_name = str(test_post['id']) + '.' + file_ext
                            file_path = Path(file_cache_dir, file_name)

                            # TODO Add a hash check to verify if they should be redownloaded?
                            if file_path.exists():
                                should_cache = False
                                file_path.touch()

                            parsed_posts.append(BooruParsedPost(test_post['id'], file_ext, file_name, file_path))
                            break

                if should_cache:
                    print(f"Caching post #{test_post['id']}...")
                    image_bytes = await net_core.fetch_image(file_url)
                    with open(file_path, 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                else:
                    print(f"Post #{test_post['id']} is already cached.")

            print("Evaluating images...")

            ground_truth = parsed_posts.pop(0)
            for hash_func in [imagehash.phash, imagehash.dhash, imagehash.average_hash, imagehash.colorhash]:
                if hash_func != imagehash.colorhash:
                    hash_param = {'hash_size': 16}
                else:
                    hash_param = {'binbits': 6}

                ground_truth.hash.append(hash_func(Image.open(ground_truth.path), **hash_param))

                for parsed_post in parsed_posts:
                    parsed_post.hash.append(hash_func(Image.open(parsed_post.path), **hash_param))

                    hash_diff = ground_truth.hash[-1] - parsed_post.hash[-1]
                    parsed_post.score.append(hash_diff)

            print(f'Scores for post #{post_id}')

            for parsed_post in parsed_posts:
                print(f"#{parsed_post.id}", parsed_post.score)
                if sum(parsed_post.score) <= 10:
                    posts = posts[1:]

        if first_post_missing_preview:
            if post['rating'] == 's' or on_nsfw_channel:
                posts.insert(0, post)

        if posts:
            if first_post_missing_preview:
                await board_cog.send_posts(channel, posts, board=board, guide=guide, show_nsfw=on_nsfw_channel, max_posts=5)
            else:
                await board_cog.send_posts(channel, posts, board=board, guide=guide, show_nsfw=on_nsfw_channel)
        else:
            match post['rating']:
                case 's' if not nsfw_culled or on_nsfw_channel:
                    return print('Removed all duplicates')
                case 's':
                    content = botstatus_cog.get_quote('cannot_show_nsfw_gallery')
                case _:
                    content = botstatus_cog.get_quote('rude_cannot_show_nsfw_gallery')

            await botstatus_cog.typing_a_message(channel, content=content, rnd_duration=[1, 2])


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Gallery(bot))
