"""Handles the use of imageboard galleries"""
import os
import re
import shutil
from pathlib import Path

import discord
import imagehash
import pixivpy_async
import tweepy
from discord.ext import commands
from PIL import Image

import koabot.utils.net as net_utils
import koabot.utils.posts as post_utils
from koabot import koakuma
from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.board import Board
from koabot.koakuma import CACHE_DIR
from koabot.patterns import HTML_TAG_OR_ENTITY_PATTERN


class Gallery(commands.Cog):
    """Gallery class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'],
                                        bot.auth_keys['twitter']['consumer_secret'])
        twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
        self.twitter_api = tweepy.API(twit_auth, wait_on_rate_limit=True)
        self.pixiv_aapi = pixivpy_async.AppPixivAPI()
        self.pixiv_refresh_token = None

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
        id_end = 'id_end' in guide['post'] and guide['post']['id_end'] or ['?']
        pattern = 'pattern' in guide['post'] and guide['post']['pattern'] or ""

        post_id = post_utils.get_name_or_id(url, start=id_start, end=id_end, pattern=pattern)
        if not post_id:
            return

        board_cog: Board = self.bot.get_cog('Board')

        post = (await board_cog.search_query(board=board, guide=guide, post_id=post_id)).json

        if not post:
            return

        # e621 fix for broken API
        if 'post' in post:
            post = post['post']

        post_id = post['id']

        bot_cog: BotStatus = self.bot.get_cog('BotStatus')
        on_nsfw_channel = channel.is_nsfw()
        first_post_missing_preview = post_utils.post_is_missing_preview(post, board=board)
        posts = []

        if post['rating'] != 's' and not on_nsfw_channel:
            # Silently ignore
            return
            # embed = discord.Embed()
            # if 'nsfw_placeholder' in self.bot.assets[board]:
            #     embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
            # else:
            #     embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            # content = f"{msg.author.mention} {bot_cog.get_quote('improper_content_reminder')}"
            # await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

        if board == 'e621':
            has_children = post['relationships']['has_active_children']
            parent_id = post['relationships']['parent_id']
            c_search = f'parent:{post_id} order:id'
            p_search = [
                f'id:{parent_id}',
                f'parent:{parent_id} order:id -id:{post_id}'
            ]
        else:
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

            # e621 fix for broken API
            if 'posts' in results.json:
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

        parsed_posts = []
        if board == 'danbooru':
            file_cache_dir = os.path.join(CACHE_DIR, board, 'files')
            os.makedirs(file_cache_dir, exist_ok=True)

            test_posts = [post]
            test_posts.extend(posts)

            for test_post in test_posts:
                should_cache = True
                for res_key in self.bot.assets[board]['post_quality']:
                    if res_key in test_post:
                        url_candidate = test_post[res_key]
                        file_ext = net_utils.get_url_fileext(url_candidate)
                        if file_ext in ['png', 'jpg', 'webp']:
                            file_url = url_candidate
                            file_name = str(test_post['id']) + '.' + file_ext
                            file_path = os.path.join(file_cache_dir, file_name)

                            # TODO Add a hash check to verify if they should be redownloaded?
                            if os.path.isfile(file_path):
                                should_cache = False
                                Path(file_path).touch()

                            parsed_posts.append({
                                'id': test_post['id'],
                                'ext': file_ext,
                                'file_name': file_name,
                                'path': file_path,
                                'hash': [],
                                'score': []
                            })
                            break

                if should_cache:
                    print(f"Caching post #{test_post['id']}...")
                    image_bytes = await net_utils.fetch_image(file_url)
                    with open(os.path.join(file_cache_dir, file_name), 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                else:
                    print(f"Post #{test_post['id']} is already cached.")

            print('Evaluating images...')

            ground_truth = parsed_posts[0]
            for hash_func in [imagehash.phash, imagehash.dhash, imagehash.average_hash, imagehash.colorhash]:
                if hash_func != imagehash.colorhash:
                    hash_param = {'hash_size': 16}
                else:
                    hash_param = {'binbits': 6}

                ground_truth['hash'].append(hash_func(Image.open(ground_truth['path']), **hash_param))

                for parsed_post in parsed_posts[1:]:
                    parsed_post['hash'].append(hash_func(Image.open(parsed_post['path']), **hash_param))

                    hash_diff = ground_truth['hash'][len(ground_truth['hash']) - 1] - \
                        parsed_post['hash'][len(parsed_post['hash']) - 1]
                    parsed_post['score'].append(hash_diff)

            print(f'Scores for post #{post_id}')

            for parsed_post in parsed_posts[1:]:
                print('#' + str(parsed_post['id']), parsed_post['score'])
                if sum(parsed_post['score']) <= 10:
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
            if post['rating'] == 's' and not nsfw_culled or on_nsfw_channel:
                return print('Removed all duplicates')
            elif post['rating'] == 's':
                content = bot_cog.get_quote('cannot_show_nsfw_gallery')
            else:
                content = bot_cog.get_quote('rude_cannot_show_nsfw_gallery')

            await bot_cog.typing_a_message(channel, content=content, rnd_duration=[1, 2])

    async def get_twitter_gallery(self, msg: discord.Message, url: str, /, *, guide: dict) -> None:
        """Automatically fetch and post any image galleries from twitter
        Parameters:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the tweet
        Keywords:
            guide::dict
                The data which holds the board information
        """
        channel: discord.TextChannel = msg.channel
        guide = guide or self.bot.guides['gallery']['twitter-gallery']

        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end']

        post_id = post_utils.get_name_or_id(url, start=id_start, end=id_end)
        if not post_id:
            return

        try:
            tweet = self.twitter_api.get_status(post_id, tweet_mode='extended')
        except tweepy.HTTPException as e:
            # Error codes: https://developer.twitter.com/en/support/twitter-api/error-troubleshooting
            if e.response is not None:
                code = e.response.status
                print(f"Failure on Tweet #{post_id}: [E{code}]")
            else:
                print(f"Failure on Tweet #{post_id}")

            print(e)
            return

        if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
            print('Preview gallery not applicable.')
            return

        # Supress original embed (sorry, desktop-only users)
        await msg.edit(suppress=True)

        gallery_pics = []
        for picture in tweet.extended_entities['media'][0:]:
            if picture['type'] != 'photo':
                return

            # Appending :orig to get a better image quality
            gallery_pics.append(f"{picture['media_url_https']}:orig")

        total_gallery_pics = len(gallery_pics)
        for picture in gallery_pics:
            total_gallery_pics -= 1

            embed = discord.Embed()
            embed.set_image(url=picture)
            embed.colour = discord.Colour.from_rgb(29, 161, 242)  # Twitter color

            # If it's the first picture to show, add author, body, and counters
            if total_gallery_pics + 1 == len(gallery_pics):
                embed.set_author(
                    name=f'{tweet.author.name} (@{tweet.author.screen_name})',
                    url=guide['post']['url'].format(tweet.author.screen_name),
                    icon_url=tweet.author.profile_image_url_https)
                embed.description = tweet.full_text[tweet.display_text_range[0]:tweet.display_text_range[1]]
                embed.add_field(name='Retweets', value=tweet.retweet_count)
                embed.add_field(name='Likes', value=tweet.favorite_count)

            # If it's the last picture to show, add a brand footer
            if total_gallery_pics <= 0:
                embed.set_footer(
                    text=guide['embed']['footer_text'] + " • Mobile-friendly viewer",
                    icon_url=self.bot.assets['twitter']['favicon'])

            await channel.send(embed=embed)

    async def get_pixiv_gallery(self, msg: discord.Message, url: str, /) -> None:
        """Automatically fetch and post any image galleries from pixiv
        Parameters:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the pixiv post
        """
        channel: discord.TextChannel = msg.channel

        post_id = post_utils.get_name_or_id(url, start=['illust_id=', '/artworks/'], pattern=r'[0-9]+')
        if not post_id:
            return

        print(f"Now starting to process pixiv link #{post_id}")
        url = f"https://www.pixiv.net/artworks/{post_id}"

        # Login
        await self.reauthenticate_pixiv()

        try:
            illust_json = await self.pixiv_aapi.illust_detail(post_id, req_auth=True)
        except pixivpy_async.PixivError as e:
            await channel.send('Odd...')
            print(e)
            return

        print(illust_json)
        if 'illust' not in illust_json:
            # too bad
            print(f'Invalid Pixiv id #{post_id}')
            return

        print(f'Pixiv auth passed! (for #{post_id})')

        bot_cog: BotStatus = self.bot.get_cog('BotStatus')
        illust = illust_json.illust
        # if illust.x_restrict != 0 and not channel.is_nsfw():
        #     embed = discord.Embed()

        #     if 'nsfw_placeholder' in self.bot.assets['pixiv']:
        #         embed.set_image(url=self.bot.assets['pixiv']['nsfw_placeholder'])
        #     else:
        #         embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

        #     content = f"{msg.author.mention} {bot_cog.get_quote('improper_content_reminder')}"

        #     bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        #     await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])
        #     return

        temp_message = await channel.send(f"***{bot_cog.get_quote('processing_long_task')}***")
        async with channel.typing():
            total_illust_pictures = illust.page_count

            if total_illust_pictures > 1:
                pictures = illust.meta_pages
            else:
                pictures = [illust]

            total_to_preview = 1
            for i, picture in enumerate(pictures[:total_to_preview]):
                print(f'Retrieving picture #{post_id}...')

                img_url = picture.image_urls.medium
                filename = net_utils.get_url_filename(img_url)

                embed = discord.Embed()
                embed.set_image(url=f'attachment://{filename}')

                if i == 0:
                    if illust.title != "無題":
                        embed.title = illust.title

                    embed.url = url
                    embed.description = re.sub(HTML_TAG_OR_ENTITY_PATTERN, ' ', illust.caption).strip()
                    embed.set_author(
                        name=illust.user.name,
                        url=f'https://www.pixiv.net/users/{illust.user.id}')

                # create if pixiv cache directory if it doesn't exist
                file_cache_dir = os.path.join(CACHE_DIR, 'pixiv', 'files')
                os.makedirs(file_cache_dir, exist_ok=True)
                image_path = os.path.join(file_cache_dir, filename)

                # cache file if it doesn't exist
                image_bytes = None
                if not os.path.exists(image_path):
                    print('Saving to cache...')
                    image_bytes = await net_utils.fetch_image(img_url, headers=koakuma.bot.assets['pixiv']['headers'])

                    with open(os.path.join(file_cache_dir, filename), 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                    image_bytes.seek(0)

                if i + 1 >= min(total_to_preview, total_illust_pictures):
                    remaining_footer = ''

                    if total_illust_pictures > total_to_preview:
                        remaining_footer = f'{total_illust_pictures - total_to_preview}+ remaining'
                    else:
                        remaining_footer = self.bot.assets['pixiv']['name']

                    embed.set_footer(
                        text=remaining_footer,
                        icon_url=self.bot.assets['pixiv']['favicon'])

                if image_bytes:
                    await msg.reply(file=discord.File(fp=image_bytes, filename=filename), embed=embed, mention_author=False)
                    image_bytes.close()
                else:
                    print('Uploading from cache...')
                    await msg.reply(file=discord.File(fp=image_path, filename=filename), embed=embed, mention_author=False)

        await temp_message.delete()
        await msg.edit(suppress=True)

        print('DONE PIXIV!')

    async def reauthenticate_pixiv(self) -> None:
        """Fetch and cache the refresh token"""
        if self.pixiv_refresh_token:
            return await self.pixiv_aapi.login(refresh_token=self.pixiv_refresh_token)

        pixiv_cache_dir = os.path.join(CACHE_DIR, 'pixiv')
        token_filename = 'refresh_token'
        token_path = os.path.join(pixiv_cache_dir, token_filename)

        if os.path.exists(token_path):
            with open(token_path, encoding="UTF-8") as token_file:
                token = token_file.readline()
                self.pixiv_refresh_token = token
                await self.pixiv_aapi.login(refresh_token=token)
        else:
            pixiv_auth = self.bot.auth_keys['pixiv']
            await self.pixiv_aapi.login(pixiv_auth['username'], pixiv_auth['password'])
            self.pixiv_refresh_token = self.pixiv_aapi.refresh_token
            os.makedirs(pixiv_cache_dir, exist_ok=True)
            with open(token_path, 'w', encoding="UTF-8") as token_file:
                token_file.write(self.pixiv_aapi.refresh_token)

    async def get_deviantart_post(self, msg: discord.Message, url: str, /) -> None:
        """Automatically fetch post from deviantart"""

        channel: discord.TextChannel = msg.channel

        post_id = post_utils.get_name_or_id(url, start='/art/', pattern=r'[0-9]+$')
        if not post_id:
            return

        search_url = self.bot.assets['deviantart']['search_url_extended'].format(post_id)
        api_result = (await net_utils.http_request(search_url, json=True, err_msg=f'error fetching post #{post_id}')).json

        deviation = api_result['deviation']

        if deviation['type'] == "image":
            await msg.edit(suppress=True)
            await self.send_deviantart_image(channel, url, deviation)
        elif deviation['type'] == "literature":
            await msg.edit(suppress=True)
            await self.send_deviantart_literature(channel, url,  deviation)
        else:
            print(f"Incapable of handling DeviantArt url (type: {deviation['type']}):\n{url}")

    async def send_deviantart_image(self, channel: discord.TextChannel, url: str, deviation):
        """DeviantArt image embed sender"""

        token = deviation['media']['token'][0]
        base_uri = deviation['media']['baseUri']
        pretty_name = deviation['media']['prettyName']

        for media_type in deviation['media']['types']:
            if media_type['t'] == 'preview':
                preview_url = media_type['c'].replace('<prettyName>', pretty_name)
                break

        image_url = f'{base_uri}/{preview_url}?token={token}'
        print(image_url)

        embed = discord.Embed()
        embed.title = deviation['title']
        embed.url = url
        embed.color = 0x06070d
        embed.set_author(
            name=deviation['author']['username'],
            url=f"https://www.deviantart.com/{deviation['author']['username']}",
            icon_url=deviation['author']['usericon'])

        embed.description = re.sub(HTML_TAG_OR_ENTITY_PATTERN, ' ',
                                   deviation['extended']['description']).strip()

        if len(embed.description) > 200:
            embed.description = embed.description[:200] + "..."

        if (da_favorites := deviation['stats']['favourites']) > 0:
            embed.add_field(name='Favorites', value=f"{da_favorites:,}")

        if (da_views := deviation['extended']['stats']['views']) > 0:
            embed.add_field(name='Views', value=f"{da_views:,}")

        embed.set_image(url=image_url)
        embed.set_footer(
            text=self.bot.assets['deviantart']['name'],
            icon_url=self.bot.assets['deviantart']['favicon'])

        await channel.send(embed=embed)

    async def send_deviantart_literature(self, channel: discord.TextChannel, url: str, deviation):
        """DeviantArt literature embed sender"""

        embed = discord.Embed()
        embed.title = deviation['title']
        embed.url = url
        embed.color = 0x06070d
        embed.set_author(
            name=deviation['author']['username'],
            url=f"https://www.deviantart.com/{deviation['author']['username']}",
            icon_url=deviation['author']['usericon'])

        embed.description = deviation['textContent']['excerpt'] + "..."

        if (da_favorites := deviation['stats']['favourites']) > 0:
            embed.add_field(name='Favorites', value=f"{da_favorites:,}")

        if (da_views := deviation['extended']['stats']['views']) > 0:
            embed.add_field(name='Views', value=f"{da_views:,}")

        embed.set_footer(
            text=self.bot.assets['deviantart']['name'],
            icon_url=self.bot.assets['deviantart']['favicon'])

        await channel.send(embed=embed)

    async def get_imgur_gallery(self, msg: discord.Message, url: str):
        """Automatically fetch and post any image galleries from imgur"""

        channel: discord.TextChannel = msg.channel

        album_id = post_utils.get_name_or_id(url, start=['/a/', '/gallery/'])
        if not album_id:
            return

        search_url = self.bot.assets['imgur']['album_url'].format(album_id)
        api_result = (await net_utils.http_request(search_url, headers=self.bot.assets['imgur']['headers'], json=True)).json

        if not api_result or api_result['status'] != 200:
            return

        total_album_pictures = len(api_result['data']) - 1

        if total_album_pictures < 1:
            return

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

            await channel.send(embed=embed)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Gallery(bot))
