"""Handles the use of imageboard galleries"""
import datetime
import html
import os
import re
import shutil
from io import BytesIO
from pathlib import Path

import asyncpraw
import discord
import imagehash
import pixivpy_async
import tweepy
from asyncpraw.reddit import Submission, Subreddit
from discord.ext import commands
from PIL import Image
from thefuzz import fuzz

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.core.embed import EmbedGroup
from koabot.kbot import KBot
from koabot.patterns import HTML_TAG_OR_ENTITY_PATTERN


class BooruParsedPost():
    def __init__(self, id_, ext, filename, path) -> None:
        self.id: int = id_
        self.ext = ext
        self.filename = filename
        self.path = path
        self.hash = []
        self.score = []


class PixivHelper():
    def __init__(self) -> None:
        self.files: list[discord.File] = []
        self.embeds: list[discord.Embed] = []

    def add_file(self, fp: BytesIO | str, filename: str) -> None:
        self.files.append(discord.File(fp=fp, filename=filename))

    def add_embed(self, embed: discord.Embed) -> None:
        self.embeds.append(embed)


class SitePreview(commands.Cog):
    """Site preview"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')


class Patreon(SitePreview):
    """Patreon site preview"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)

    def get_id(self, url: str) -> str:
        return post_core.get_name_or_id(url, start='/posts/', pattern=r'[0-9]+$')

    async def get_patreon_gallery(self, msg: discord.Message, url: str):
        if not (post_id := self.get_id(url)):
            return


class Twitter(SitePreview):
    """Twitter site preview"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self._twitter_api: tweepy.API = None

    @property
    def twitter_api(self) -> tweepy.API:
        if not self._twitter_api:
            twit_keys = self.bot.auth_keys['twitter']
            twit_auth = tweepy.OAuthHandler(twit_keys['consumer'], twit_keys['consumer_secret'])
            twit_auth.set_access_token(twit_keys['token'], twit_keys['token_secret'])
            self._twitter_api = tweepy.API(twit_auth, wait_on_rate_limit=True)

        return self._twitter_api

    def get_id(self, guide: dict, url: str) -> str:
        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end']

        return post_core.get_name_or_id(url, start=id_start, end=id_end)

    def get_tweet(self, tweet_id) -> tweepy.Tweet:
        try:
            return self.twitter_api.get_status(tweet_id, tweet_mode="extended")
        except tweepy.HTTPException as e:
            # Error codes: https://developer.twitter.com/en/support/twitter-api/error-troubleshooting
            if e.response is not None:
                code = e.response.status
                print(f"Failure on Tweet #{tweet_id}: [E{code}]")
            else:
                print(f"Failure on Tweet #{tweet_id}")
            print(e)
        return None

    async def get_twitter_gallery(self, msg: discord.Message, url: str, /, *, guide: dict = None) -> None:
        """Automatically fetch and post any image galleries from twitter
        Arguments:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the tweet
        Keywords:
            guide::dict
                The data which holds the board information
        """
        guide = guide or self.bot.guides['gallery']['twitter-gallery']

        if not (post_id := self.get_id(guide, url)):
            return

        if not (tweet := self.get_tweet(post_id)):
            return

        if not hasattr(tweet, 'extended_entities'):
            return print("Twitter preview not applicable. (No extended entities)")

        if len((tweet_ee_media := tweet.extended_entities['media'])) == 1:
            match tweet_ee_media[0]['type']:
                case 'photo':
                    if not hasattr(tweet, 'possibly_sensitive') or not tweet.possibly_sensitive:
                        return print("Twitter preview not applicable. (Media photo is sfw)")

                    # TODO: There's got to be a better way...
                    if guide['embed']['footer_text'] == "TwitFix":
                        return print("Twitter preview not applicable. (Handled by TwitFix)")

                case _:  # 'video' or 'animated_gif'
                    if guide['embed']['footer_text'] == "TwitFix":
                        return print("Twitter preview not applicable. (Handled by TwitFix)")

                    if hasattr(tweet, 'possibly_sensitive') and tweet.possibly_sensitive:
                        fixed_url = url.replace("twitter", "fxtwitter", 1)
                        await msg.reply(content=f"Sorry! Due to Discord's API limitations I cannot embed videos. (Twitter disallows NSFW previews)\n{fixed_url}", mention_author=False)

                    return

        # Appending :orig to get a better image quality
        gallery_pics = [f"{picture['media_url_https']}:orig" for picture in tweet_ee_media]

        embed_group = EmbedGroup()
        embed_group.color = discord.Colour(int(guide['embed']['color'], 16))

        # If it's the first picture to show, add author, body, and counters
        if (tw_likes := tweet.favorite_count) > 0:
            embed_group.first.add_field(name='Likes', value=f"{tw_likes:,}")
        if (tw_retweets := tweet.retweet_count) > 0:
            embed_group.first.add_field(name='Retweets', value=f"{tw_retweets:,}")

        embed_group.first.set_author(
            name=f'{tweet.author.name} (@{tweet.author.screen_name})',
            url=guide['post']['url'].format(tweet.author.screen_name),
            icon_url=tweet.author.profile_image_url_https)

        # int, int = list[int] (2 elements)
        range_start, range_end = tweet.display_text_range
        embed_group.first.description = html.unescape(tweet.full_text[range_start:range_end])

        # If it's the last picture to show, add a brand footer
        embed_group.last.set_footer(
            text=guide['embed']['footer_text'] + " • Mobile-friendly viewer",
            icon_url=self.bot.assets['twitter']['favicon'])
        embed_group.last.timestamp = datetime.datetime.now(datetime.timezone.utc)

        for picture in gallery_pics:
            embed_group.add().set_image(url=picture)

        await msg.reply(embeds=embed_group.embeds, mention_author=False)

        # Supress original embed (sorry, desktop-only users)
        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden as e:
            # Missing Permissions
            match e.code:
                case 50013:
                    print("Missing Permissions: Cannot suppress embed from sender's message")
                case _:
                    print(f"Forbidden: Status {e.status} (code {e.code}")


class Pixiv(SitePreview):
    """Pixiv site preview"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.pixiv_refresh_token: str = None
        self._pixiv_aapi: pixivpy_async.AppPixivAPI = None

    @property
    def pixiv_aapi(self) -> pixivpy_async.AppPixivAPI:
        if not self._pixiv_aapi:
            self._pixiv_aapi = pixivpy_async.AppPixivAPI()

        return self._pixiv_aapi

    def get_id(self, url: str) -> str:
        return post_core.get_name_or_id(url, start=['illust_id=', '/artworks/'], pattern=r'[0-9]+')

    async def get_pixiv_gallery(self, msg: discord.Message, url: str, /, *, only_missing_preview: bool = False) -> None:
        """Automatically fetch and post any image galleries from pixiv
        Arguments:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the pixiv post
            only_missing_preview::bool
                Only shows a preview if the native embed is missing from the original link. Default is False
        """
        channel: discord.TextChannel = msg.channel

        if not (post_id := self.get_id(url)):
            return

        print(f"Now starting to process pixiv #{post_id}")
        url = f"https://www.pixiv.net/artworks/{post_id}"

        # Login
        await self.reauthenticate_pixiv()

        try:
            illust_json = await self.pixiv_aapi.illust_detail(post_id, req_auth=True)
        except pixivpy_async.PixivError as e:
            await channel.send("Odd...")
            return print(e)

        if 'illust' not in illust_json:
            # too bad
            return print(f"Invalid Pixiv id #{post_id}")

        print(f"Pixiv auth passed! (for #{post_id})")

        # botstatus_cog = self.botstatus
        illust = illust_json.illust

        # if illust.x_restrict != 0 and not channel.is_nsfw():
        #     embed = discord.Embed()

        #     if 'nsfw_placeholder' in self.bot.assets['pixiv']:
        #         embed.set_image(url=self.bot.assets['pixiv']['nsfw_placeholder'])
        #     else:
        #         embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

        #     content = f"{msg.author.mention} {botstatus_cog.get_quote('improper_content_reminder')}"

        #     await botstatus_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])
        #     return

        async with channel.typing():
            total_illust_pictures = illust.page_count
            pictures = illust.meta_pages if total_illust_pictures > 1 else [illust]
            total_to_preview = 1 if only_missing_preview else 5

            pixiv_helper = PixivHelper()
            pictures = pictures[:total_to_preview]
            for i, picture in enumerate(pictures):
                print(f"Retrieving from #{post_id} picture {i + 1}/{len(pictures)}...")

                img_url = picture.image_urls.medium
                filename = net_core.get_url_filename(img_url)

                embed = discord.Embed()
                embed.set_image(url=f'attachment://{filename}')

                if i == 0:
                    if illust.title != "無題":
                        embed.title = illust.title

                    embed.url = url
                    description = re.sub(r'<br \/>', '\n', illust.caption)
                    description = re.sub(HTML_TAG_OR_ENTITY_PATTERN, ' ', description)
                    embed.description = description.strip()

                    if (px_bookmarks := illust.total_bookmarks) > 0:
                        embed.add_field(name='Bookmarks', value=f"{px_bookmarks:,}")

                    if (px_views := illust.total_view) > 0:
                        embed.add_field(name='Views', value=f"{px_views:,}")

                    embed.set_author(name=illust.user.name,
                                     url=f"https://www.pixiv.net/users/{illust.user.id}")

                    # Thanks Pixiv... even your avatars are inaccessible!
                    # //////////////////////////////////////////////////////////////////
                    # avatar_url = illust.user.profile_image_urls.medium
                    # avatar_filename = net_utils.get_url_filename(avatar_url)
                    # avatar_cache_dir = os.path.join(self.bot.CACHE_DIR, 'pixiv', 'avatars')
                    # os.makedirs(avatar_cache_dir, exist_ok=True)
                    # avatar_path = os.path.join(avatar_cache_dir, avatar_filename)

                    # # cache file if it doesn't exist
                    # image_bytes = None
                    # if not os.path.exists(image_path):
                    #     print('Saving to cache...')
                    #     image_bytes = await net_core.fetch_image(avatar_url, headers=self.bot.assets['pixiv']['headers'])

                    #     with open(os.path.join(avatar_cache_dir, avatar_filename), 'wb') as image_file:
                    #         shutil.copyfileobj(image_bytes, image_file)
                    #     image_bytes.seek(0)

                # create if pixiv cache directory if it doesn't exist
                file_cache_dir = os.path.join(self.bot.CACHE_DIR, 'pixiv', 'files')
                os.makedirs(file_cache_dir, exist_ok=True)
                image_path = os.path.join(file_cache_dir, filename)

                # cache file if it doesn't exist
                image_bytes = None
                if not os.path.exists(image_path):
                    print("Saving to cache...")
                    image_bytes = await net_core.fetch_image(img_url, headers=self.bot.assets['pixiv']['headers'])

                    with open(os.path.join(file_cache_dir, filename), 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                    image_bytes.seek(0)

                if i + 1 >= min(total_to_preview, total_illust_pictures):
                    if total_illust_pictures > total_to_preview:
                        remaining_footer = f"{total_illust_pictures - total_to_preview}+ remaining"
                    else:
                        remaining_footer = self.bot.assets['pixiv']['name']

                    embed.set_footer(
                        text=remaining_footer,
                        icon_url=self.bot.assets['pixiv']['favicon'])

                if image_bytes:
                    pixiv_helper.add_file(image_bytes, filename)
                    image_bytes.close()
                else:
                    print("Uploading from cache...")
                    pixiv_helper.add_file(image_path, filename)

                pixiv_helper.add_embed(embed)

        await msg.reply(files=pixiv_helper.files, embeds=pixiv_helper.embeds, mention_author=False)

        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden as e:
            # Missing Permissions
            match e.code:
                case 50013:
                    print("Missing Permissions: Cannot suppress embed from sender's message")
                case _:
                    print(f"Forbidden: Status {e.status} (code {e.code}")

        print('DONE PIXIV!')

    async def reauthenticate_pixiv(self) -> None:
        """Fetch and cache the refresh token"""
        if self.pixiv_refresh_token:
            return await self.pixiv_aapi.login(refresh_token=self.pixiv_refresh_token)

        pixiv_cache_dir = os.path.join(self.bot.CACHE_DIR, 'pixiv')
        token_filename = 'refresh_token'
        token_path = os.path.join(pixiv_cache_dir, token_filename)

        if os.path.exists(token_path):
            with open(token_path, encoding="UTF-8") as token_file:
                self.pixiv_refresh_token = token_file.readline()
                await self.pixiv_aapi.login(refresh_token=self.pixiv_refresh_token)
        else:
            pix_keys = self.bot.auth_keys['pixiv']
            await self.pixiv_aapi.login(pix_keys['username'], pix_keys['password'])
            self.pixiv_refresh_token = self.pixiv_aapi.refresh_token
            os.makedirs(pixiv_cache_dir, exist_ok=True)
            with open(token_path, 'w', encoding="UTF-8") as token_file:
                token_file.write(self.pixiv_refresh_token)


class Gallery(commands.Cog):
    """Gallery class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

        self._twitter_api: tweepy.API = None
        self._reddit_api: asyncpraw.Reddit = None

    @property
    def board(self) -> Board:
        return self.bot.get_cog('Board')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def reddit_api(self) -> asyncpraw.Reddit:
        if not self._reddit_api:
            rdt_keys = self.bot.auth_keys['reddit']
            self._reddit_api = asyncpraw.Reddit(client_id=rdt_keys['client_id'],
                                                client_secret=rdt_keys['client_secret'],
                                                username=rdt_keys['username'],
                                                password=rdt_keys['password'],
                                                user_agent=rdt_keys['headers']['User-Agent'])
        return self._reddit_api

    async def display_static(self, channel: discord.TextChannel, url: str, /, *, board: str = 'danbooru', guide: dict, only_missing_preview: bool = False) -> None:
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
            only_missing_preview::bool
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

        if only_missing_preview:
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
            file_cache_dir = os.path.join(self.bot.CACHE_DIR, board, 'files')
            os.makedirs(file_cache_dir, exist_ok=True)

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
                            file_path = os.path.join(file_cache_dir, file_name)

                            # TODO Add a hash check to verify if they should be redownloaded?
                            if os.path.isfile(file_path):
                                should_cache = False
                                Path(file_path).touch()

                            parsed_posts.append(BooruParsedPost(test_post['id'], file_ext, file_name, file_path))
                            break

                if should_cache:
                    print(f"Caching post #{test_post['id']}...")
                    image_bytes = await net_core.fetch_image(file_url)
                    with open(os.path.join(file_cache_dir, file_name), 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                else:
                    print(f"Post #{test_post['id']} is already cached.")

            print('Evaluating images...')

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

    async def get_deviantart_post(self, msg: discord.Message, url: str, /) -> None:
        """Automatically fetch post from deviantart"""

        if not (post_id := post_core.get_name_or_id(url, start='/art/', pattern=r'[0-9]+$')):
            return

        # TODO: Implement oEmbed if it looks possible! json responses are extremely shorter!
        # search_url = f"https://backend.deviantart.com/oembed?url={post_id}"

        search_url = self.bot.assets['deviantart']['search_url_extended'].format(post_id)
        api_result = (await net_core.http_request(search_url, json=True, err_msg=f'error fetching post #{post_id}')).json

        deviation = api_result['deviation']

        match (deviation_type := deviation['type']):
            case 'image' | 'literature':
                embed = self.build_deviantart_embed(url, deviation)
            case _:
                print(f"Incapable of handling DeviantArt url (type: {deviation_type}):\n{url}")
                return

        await msg.reply(embed=embed, mention_author=False)

        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden as e:
            # Missing Permissions
            match e.code:
                case 50013:
                    print("Missing Permissions: Cannot suppress embed from sender's message")
                case _:
                    print(f"Forbidden: Status {e.status} (code {e.code}")

    async def get_deviantart_posts(self, msg: discord.Message, urls: list[str]):
        """Automatically fetch multiple posts from deviantart"""

        title_to_test_against = urls[0].split('/')[-1].rsplit('-', maxsplit=1)[0]
        similarity_ratio = 0
        for url in urls[1:]:
            title = url.split('/')[-1].rsplit('-', maxsplit=1)[0]
            similarity_ratio += fuzz.ratio(title, title_to_test_against)
            print(f"{title}: {title_to_test_against} ({fuzz.ratio(title, title_to_test_against)})")

        similarity_ratio /= len(urls) - 1
        print(f"Url similarity ratio: {similarity_ratio}")
        if similarity_ratio < 90:
            return

        base_type: str = None
        api_results = []
        for url in urls:
            if not (post_id := post_core.get_name_or_id(url, start='/art/', pattern=r'[0-9]+$')):
                return

            search_url = self.bot.assets['deviantart']['search_url_extended'].format(post_id)
            api_result = (await net_core.http_request(search_url, json=True, err_msg=f'error fetching post #{post_id}')).json

            deviation = api_result['deviation']

            if base_type is None:
                base_type = deviation['type']

            if deviation['type'] != base_type:
                print("Preview not available. Deviation types differ.")
                return

            api_results.append(api_result)

        embeds: list[discord.Embed] = []
        total_da_count = len(api_results)
        last_embed_index = min(4, total_da_count - 1)
        for i, deviation in enumerate([d['deviation'] for d in api_results[:5]]):
            if i != last_embed_index:
                if i == 0:
                    embed = self.build_deviantart_embed(urls[i], deviation)
                    embed.remove_footer()
                else:
                    embed = self.build_deviantart_embed(urls[i], deviation, image_only=True)
            if i == last_embed_index:
                embed = self.build_deviantart_embed(urls[i], deviation)
                embed.description = ""
                embed.remove_author()
                embed.clear_fields()
                if total_da_count > 5:
                    embed.set_footer(text=f"{total_da_count - 5}+ remaining", icon_url=embed.footer.icon_url)

            embeds.append(embed)

        await msg.reply(embeds=embeds, mention_author=False)

        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden as e:
            # Missing Permissions
            match e.code:
                case 50013:
                    print("Missing Permissions: Cannot suppress embed from sender's message")
                case _:
                    print(f"Forbidden: Status {e.status} (code {e.code}")

    def build_deviantart_embed(self, url: str, deviation: dict, *, image_only=False) -> discord.Embed:
        """DeviantArt embed builder"""

        embed = discord.Embed()
        embed.title = deviation['title']
        embed.url = url
        embed.color = 0x06070d

        if not image_only:
            author = deviation['author']
            embed.set_author(
                name=author['username'],
                url=f"https://www.deviantart.com/{author['username']}",
                icon_url=author['usericon'])

        match deviation['type']:
            case 'image' if 'prettyName' in deviation['media']:
                # 'image' is an static image or a gif
                deviation_media = deviation['media']
                token = deviation_media['token'][0]
                base_uri = deviation_media['baseUri']
                pretty_name = deviation_media['prettyName']

                image_url = ""
                valid_types = ["gif", "preview"]
                for media_type in deviation_media['types']:
                    match media_type['t']:
                        case "gif":
                            if "gif" not in valid_types:
                                continue

                            valid_types = valid_types[:valid_types.index("gif")]
                            image_url = media_type['b']
                        case "preview":
                            if "preview" not in valid_types:
                                continue

                            valid_types = valid_types[:valid_types.index("preview")]
                            preview_url = media_type['c'].replace('<prettyName>', pretty_name)
                            preview_url = preview_url.replace(',q_80', ',q_100')
                            image_url = f"{base_uri}{preview_url}"

                image_url = f"{image_url}?token={token}"

                if 'description' in deviation['extended'] and not image_only:
                    embed.description = re.sub(HTML_TAG_OR_ENTITY_PATTERN, ' ',
                                               deviation['extended']['description']).strip()

                if embed.description and len(embed.description) > 200:
                    embed.description = embed.description[:200] + "..."

                embed.set_image(url=image_url)
            case 'image':
                # 'image' assumed to be a gif
                deviation_media = deviation['media']
                token = deviation_media['token'][0]

                for media_type in deviation_media['types']:
                    if media_type['t'] == 'gif':
                        preview_url = media_type['b']
                        image_url = f"{preview_url}?token={token}"
                        break

                if 'description' in deviation['extended'] and not image_only:
                    embed.description = re.sub(HTML_TAG_OR_ENTITY_PATTERN, ' ',
                                               deviation['extended']['description']).strip()

                if len(embed.description) > 200:
                    embed.description = embed.description[:200] + "..."

                embed.set_image(url=image_url)
            case 'literature':
                embed.description = deviation['textContent']['excerpt'] + "..."
            case _:
                raise ValueError("Unknown DeviantArt embed type!")

        if not image_only:
            if (da_favorites := deviation['stats']['favourites']) > 0:
                embed.add_field(name='Favorites', value=f"{da_favorites:,}")

            if (da_views := deviation['extended']['stats']['views']) > 0:
                embed.add_field(name='Views', value=f"{da_views:,}")

            embed.set_footer(
                text=self.bot.assets['deviantart']['name'],
                icon_url=self.bot.assets['deviantart']['favicon'])

        return embed

    async def get_imgur_gallery(self, msg: discord.Message, url: str):
        """Automatically fetch and post any image galleries from imgur"""
        if not (album_id := post_core.get_name_or_id(url, start=['/a/', '/gallery/'])):
            return

        search_url = self.bot.assets['imgur']['album_url'].format(album_id)
        api_result = (await net_core.http_request(search_url, headers=self.bot.assets['imgur']['headers'], json=True)).json

        if not api_result or api_result['status'] != 200:
            return

        # TODO: Why -1?
        if (total_album_pictures := len(api_result['data']) - 1) < 1:
            return

        embeds_to_send = []
        pictures_processed = 0
        for image in api_result['data'][1:5]:
            pictures_processed += 1

            embed = discord.Embed()
            embed.set_image(url=image['link'])

            if pictures_processed >= min(4, total_album_pictures):
                remaining_footer = ''

                if total_album_pictures > 4:
                    remaining_footer = f'{total_album_pictures - 4}+ remaining'
                else:
                    remaining_footer = self.bot.assets['imgur']['name']

                embed.set_footer(
                    text=remaining_footer,
                    icon_url=self.bot.assets['imgur']['favicon']['size32'])

            embeds_to_send.append(embed)

        await msg.reply(embeds=embeds_to_send, mention_author=False)

    async def get_reddit_gallery(self, msg: discord.Message, url: str, /, *, guide: dict):
        """Automatically post Reddit galleries whenever possible"""
        reddit_url_prefix = "https://" + guide['post']['url']
        submission: Submission = await self.reddit_api.submission(url=url)

        # Don't override videos
        if submission.is_video:
            return print("Preview preview not applicable. (reddit hosted video)")
        elif hasattr(submission, 'post_hint'):
            match submission.post_hint:
                case "hosted:video":
                    return print("Preview preview not applicable. (reddit hosted video)")
                case "rich:video":
                    return print("Preview preview not applicable. (rich video)")

        subreddit: Subreddit = submission.subreddit
        await subreddit.load()

        subreddit_icon = subreddit.community_icon if subreddit.community_icon else subreddit.icon_img

        header_embed = discord.Embed()
        header_embed.set_author(name=submission.subreddit_name_prefixed,
                                url=f"{reddit_url_prefix}/{submission.subreddit_name_prefixed}",
                                icon_url=subreddit_icon)
        header_embed.title = submission.title
        header_embed.url = f"{reddit_url_prefix}{submission.permalink}"
        header_embed.add_field(name='Score', value=f"{submission.score:,}")
        header_embed.add_field(name='Comments', value=f"{submission.num_comments:,}")
        footer_text = guide['embed']['footer_text']

        if submission.selftext:
            max_post_length = 350   # arbitrary maximum
            if len(submission.selftext) > max_post_length:
                # TODO: Even though the output is nicer, this removes newlines.
                # header_embed.description = textwrap.shorten(
                # submission.selftext, width=max_post_length, placeholder="...")
                # TODO: Disjointed markdown is not cleaned up
                # i.e. the closing ** is cut off
                header_embed.description = submission.selftext[:max_post_length - 1] + "…"
            else:
                header_embed.description = submission.selftext

        # Determine whether or not to post without thumbnail blur
        obfuscated_preview = False
        if not msg.channel.is_nsfw():
            obfuscated_preview = submission.over_18

        embeds = [header_embed]
        # Post has a media gallery
        if hasattr(submission, 'gallery_data'):
            media_count = len(submission.gallery_data['items'])
            ordered_media_data = sorted(submission.gallery_data['items'], key=lambda x: x['id'])
            media_type = 'p'        # TODO: p = stands for preview?
            total_to_preview = 4

            if obfuscated_preview:
                media_type = 'o'    # TODO: o = stands for obfuscated?
                total_to_preview = 1

            for i, item_data in enumerate(ordered_media_data[:total_to_preview]):
                media_element = submission.media_metadata[item_data['media_id']]
                if i == 0:
                    embed = header_embed
                else:
                    embed = discord.Embed()
                    embeds.append(embed)

                if media_element['e'] == "Image":
                    # Fetching the last element from the resolutions list (highest preview-friendly res)
                    post_preview = media_element[media_type][-1]['u']
                    embed.set_image(url=post_preview)

                # TODO: Another len() - 1 case to change
                # If we're on the last element
                if i == len(ordered_media_data[:total_to_preview]) - 1:
                    if media_count > total_to_preview:
                        footer_text = f"{media_count - total_to_preview}+ remaining"

        # Post has only one media element
        elif hasattr(submission, 'preview') and 'images' in submission.preview:
            preview_root = submission.preview['images'][0]

            # Use blurred-out previews on NSFW posts in SFW channels
            if obfuscated_preview:
                preview_root = preview_root['variants']['nsfw']
            # Show gifs instead if available
            elif 'variants' in preview_root and 'gif' in preview_root['variants']:
                preview_root = preview_root['variants']['gif']

            post_preview = preview_root['resolutions'][-1]['url']
            header_embed.set_image(url=post_preview)

        embeds[-1].set_footer(text=footer_text, icon_url=guide['embed']['favicon']['size192'])

        await msg.reply(embeds=embeds, mention_author=False)

        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden as e:
            # Missing Permissions
            match e.code:
                case 50013:
                    print("Missing Permissions: Cannot suppress embed from sender's message")
                case _:
                    print(f"Forbidden: Status {e.status} (code {e.code}")


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SitePreview(bot))
    await bot.add_cog(Patreon(bot))
    await bot.add_cog(Twitter(bot))
    await bot.add_cog(Pixiv(bot))
    await bot.add_cog(Gallery(bot))
