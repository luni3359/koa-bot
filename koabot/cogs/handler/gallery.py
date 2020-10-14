"""Handles the use of imageboard galleries"""
import os
import random
import shutil
import typing
from pathlib import Path

import discord
import imagehash
import pixivpy3
import tweepy
from discord.ext import commands
from PIL import Image

import koabot.koakuma as koakuma
import koabot.utils as utils
from koabot.koakuma import CACHE_DIR


class Gallery(commands.Cog):
    """Gallery class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'], bot.auth_keys['twitter']['consumer_secret'])
        twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
        self.twitter_api = tweepy.API(twit_auth, wait_on_rate_limit=True)
        self.pixiv_api = pixivpy3.AppPixivAPI()
        self.pixiv_refresh_token = None

    async def display_static(self, channel, msg, url, **kwargs):
        """Display posts from a gallery in separate unmodifiable embeds
        Arguments:
            channel::discord.TextChannel
                Channel the message is in
            msg::discord.Message
                Message sent by the author
            url::str
                Url to get a gallery from
        Keywords:
            board::str
                Name of the board to handle. Default is 'danbooru'
            id_start::str
                The point at which an url's id is stripped from
            id_end::str
                The point at which an url's id is stripped to
                The board to handle. Default is 'danbooru'
            guide::dict
                The data which holds the board information
            end_regex::bool
                Whether or not id_end is regex. Default is False
        """

        board = kwargs.get('board', 'danbooru')
        guide = kwargs.get('guide', None)
        end_regex = kwargs.get('end_regex', False)

        if not guide:
            raise ValueError('The \'guide\' keyword argument is not defined.')

        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end']

        on_nsfw_channel = channel.is_nsfw()
        post_id = utils.posts.get_post_id(url, id_start, id_end, has_regex=end_regex)

        if not post_id:
            return

        board_cog = self.bot.get_cog('Board')

        post = (await board_cog.search_query(board=board, guide=guide, post_id=post_id)).json

        if not post:
            return

        # e621 fix for broken API
        if 'post' in post:
            post = post['post']

        post_id = post['id']

        bot_cog = self.bot.get_cog('BotStatus')
        on_nsfw_channel = channel.is_nsfw()
        first_post_missing_preview = utils.posts.post_is_missing_preview(post, board=board)
        posts = []

        if post['rating'] != 's' and not on_nsfw_channel:
            embed = discord.Embed()
            if 'nsfw_placeholder' in self.bot.assets[board]:
                embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
            else:
                embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            content = f"{msg.author.mention} {random.choice(self.bot.quotes['improper_content_reminder'])}"
            await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

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

        if has_children:
            search = c_search
        elif parent_id:
            search = p_search
        else:
            if first_post_missing_preview:
                if post['rating'] == 's' or on_nsfw_channel:
                    await board_cog.send_posts(channel, post, board=board, guide=guide)
            return

        if isinstance(search, str):
            search = [search]

        for s in search:
            results = (await board_cog.search_query(board=board, guide=guide, tags=s, include_nsfw=on_nsfw_channel)).json

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
                        file_ext = utils.net.get_url_fileext(url_candidate)
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
                    image_bytes = await utils.net.fetch_image(file_url)
                    with open(os.path.join(file_cache_dir, file_name), 'wb') as image_file:
                        shutil.copyfileobj(image_bytes, image_file)
                else:
                    print(f"Post #{test_post['id']} is already cached.")

            print('Evaluating images...')

            ground_truth = parsed_posts[0]
            for hash_func in [imagehash.phash, imagehash.dhash, imagehash.average_hash, imagehash.colorhash]:
                if hash_func == imagehash.colorhash:
                    hash_param = {'binbits': 6}
                else:
                    hash_param = {'hash_size': 16}

                ground_truth['hash'].append(hash_func(Image.open(ground_truth['path']), **hash_param))

                for parsed_post in parsed_posts[1:]:
                    parsed_post['hash'].append(hash_func(Image.open(parsed_post['path']), **hash_param))

                    hash_diff = ground_truth['hash'][len(ground_truth['hash']) - 1] - parsed_post['hash'][len(parsed_post['hash']) - 1]
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
                print('Removed all duplicates')
                return
            elif post['rating'] == 's':
                content = random.choice(self.bot.quotes['cannot_show_nsfw_gallery'])
            else:
                content = random.choice(self.bot.quotes['rude_cannot_show_nsfw_gallery'])

            await bot_cog.typing_a_message(channel, content=content, rnd_duration=[1, 2])

    async def get_twitter_gallery(self, msg, url, **kwargs):
        """Automatically fetch and post any image galleries from twitter
        Keywords:
            guide::dict
                The data which holds the board information
        """

        channel = msg.channel
        guide = kwargs.get('guide', self.bot.guides['gallery']['twitter-gallery'])

        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end']

        post_id = utils.posts.get_post_id(url, id_start, id_end)
        if not post_id:
            return

        tweet = self.twitter_api.get_status(post_id, tweet_mode='extended')

        if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
            print('Preview gallery not applicable.')
            return

        gallery_pics = []
        for picture in tweet.extended_entities['media'][1:]:
            if picture['type'] != 'photo':
                return

            # Appending :orig to get a better image quality
            gallery_pics.append(f"{picture['media_url_https']}:orig")

        total_gallery_pics = len(gallery_pics)
        for picture in gallery_pics:
            total_gallery_pics -= 1

            embed = discord.Embed()
            embed.set_author(
                name=f'{tweet.author.name} (@{tweet.author.screen_name})',
                url=guide['post']['url'].format(tweet.author.screen_name),
                icon_url=tweet.author.profile_image_url_https)
            embed.set_image(url=picture)

            # If it's the last picture to show, add a brand footer
            if total_gallery_pics <= 0:
                embed.set_footer(
                    text=guide['embed']['footer_text'],
                    icon_url=self.bot.assets['twitter']['favicon'])

            await channel.send(embed=embed)

    async def get_pixiv_gallery(self, msg, url):
        """Automatically fetch and post any image galleries from pixiv"""

        channel = msg.channel

        post_id = utils.posts.get_post_id(url, ['illust_id=', '/artworks/'], '&')
        if not post_id:
            return

        print(f'Now starting to process pixiv link #{post_id}')

        # Login
        if self.pixiv_api.access_token is None:
            self.reauthenticate_pixiv()
        else:
            self.pixiv_api.auth(refresh_token=self.pixiv_refresh_token)

        try:
            illust_json = self.pixiv_api.illust_detail(post_id, req_auth=True)
        except pixivpy3.PixivError as e:
            await channel.send('Odd...')
            print(e)
            return

        print(illust_json)
        if 'illust' not in illust_json:
            # too bad
            print(f'Invalid Pixiv id #{post_id}')
            return

        print(f'Pixiv auth passed! (for #{post_id})')

        illust = illust_json.illust
        if illust.x_restrict != 0 and not channel.is_nsfw():
            embed = discord.Embed()

            if 'nsfw_placeholder' in self.bot.assets['pixiv']:
                embed.set_image(url=self.bot.assets['pixiv']['nsfw_placeholder'])
            else:
                embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            content = f"{msg.author.mention} {random.choice(self.bot.quotes['improper_content_reminder'])}"

            bot_cog = self.bot.get_cog('BotStatus')

            await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])
            return

        temp_message = await channel.send(f"***{random.choice(self.bot.quotes['processing_long_task'])}***")
        async with channel.typing():
            total_illust_pictures = illust.page_count

            if total_illust_pictures > 1:
                pictures = illust.meta_pages
            else:
                pictures = [illust]

            total_to_preview = 5
            for i, picture in enumerate(pictures[:total_to_preview]):
                print(f'Retrieving picture #{post_id}...')

                (embed, url, filename) = await self.generate_pixiv_embed(picture, illust.user)

                # create if pixiv cache directory if it doesn't exist
                file_cache_dir = os.path.join(CACHE_DIR, 'pixiv', 'files')
                os.makedirs(file_cache_dir, exist_ok=True)
                image_path = os.path.join(file_cache_dir, filename)

                # cache file if it doesn't exist
                image_bytes = None
                if not os.path.exists(image_path):
                    print('Saving to cache...')
                    image_bytes = await utils.net.fetch_image(url, headers=koakuma.bot.assets['pixiv']['headers'])

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
                    await channel.send(file=discord.File(fp=image_bytes, filename=filename), embed=embed)
                    image_bytes.close()
                else:
                    print('Uploading from cache...')
                    await channel.send(file=discord.File(fp=image_path, filename=filename), embed=embed)

        await temp_message.delete()
        print('DONE PIXIV!')

    def reauthenticate_pixiv(self):
        """Fetch and cache the refresh token"""
        pixiv_cache_dir = os.path.join(CACHE_DIR, 'pixiv')
        token_filename = 'refresh_token'
        token_path = os.path.join(pixiv_cache_dir, token_filename)

        if self.pixiv_refresh_token:
            self.pixiv_api.auth(refresh_token=self.pixiv_refresh_token)
        elif os.path.exists(token_path):
            with open(token_path) as token_file:
                token = token_file.readline()
                self.pixiv_refresh_token = token
                self.pixiv_api.auth(refresh_token=token)
        else:
            self.pixiv_api.login(self.bot.auth_keys['pixiv']['username'], self.bot.auth_keys['pixiv']['password'])
            self.pixiv_refresh_token = self.pixiv_api.refresh_token
            os.makedirs(pixiv_cache_dir, exist_ok=True)
            with open(token_path, 'w') as token_file:
                token_file.write(self.pixiv_api.refresh_token)

    async def generate_pixiv_embed(self, post, user):
        """Generate embeds for pixiv urls
        Arguments:
            post
                The post object
            user
                The artist of the post
        Returns:
            embed::discord.Embed
                Embed object
            image_filename::str
                Image filename, extension included
        """

        img_url = post.image_urls.medium
        image_filename = utils.net.get_url_filename(img_url)

        embed = discord.Embed()
        embed.set_author(
            name=user.name,
            url=f'https://www.pixiv.net/member.php?id={user.id}')
        embed.set_image(url=f'attachment://{image_filename}')
        return embed, img_url, image_filename

    async def get_sankaku_post(self, msg, url):
        """Automatically fetch a bigger preview from Sankaku Complex"""

        channel = msg.channel

        post_id = utils.posts.get_post_id(url, '/show/', '?')
        if not post_id:
            return

        search_url = f"{self.bot.assets['sankaku']['id_search_url']}{post_id}"
        api_result = (await utils.net.http_request(search_url, json=True)).json

        if not api_result or 'code' in api_result:
            print(f"Sankaku error\nCode #{api_result['code']}")
            return

        valid_urls_keys = [
            'sample_url',   # medium quality / large sample
            'file_url',     # highest quality / file (png, zip, webm)
            'preview_url'   # lowest quality / thumbnail
        ]
        approved_ext = ['png', 'jpg', 'webp', 'gif']

        img_url = api_result['preview_url']
        image_filename = utils.net.get_url_filename(img_url)
        image = await utils.net.fetch_image(img_url)

        embed = discord.Embed()
        embed.set_image(url=f"attachment://{image_filename}")
        embed.set_footer(
            text=self.bot.assets['sankaku']['name'],
            icon_url=self.bot.assets['sankaku']['favicon'])

        await channel.send(file=discord.File(fp=image, filename=image_filename), embed=embed)

    async def get_deviantart_post(self, msg, url):
        """Automatically fetch post from deviantart"""

        channel = msg.channel

        post_id = utils.posts.get_post_id(url, '/art/', r'[0-9]+$', has_regex=True)
        if not post_id:
            return

        search_url = self.bot.assets['deviantart']['search_url_extended'].format(post_id)

        api_result = (await utils.net.http_request(search_url, json=True, err_msg=f'error fetching post #{post_id}')).json

        if not api_result['deviation']['isMature']:
            return

        if 'token' in api_result['deviation']['media']:
            token = api_result['deviation']['media']['token'][0]
        else:
            print('No token!!!!')

        baseUri = api_result['deviation']['media']['baseUri']
        prettyName = api_result['deviation']['media']['prettyName']

        for media_type in api_result['deviation']['media']['types']:
            if media_type['t'] == 'preview':
                preview_url = media_type['c'].replace('<prettyName>', prettyName)
                break

        image_url = f'{baseUri}/{preview_url}?token={token}'
        print(image_url)

        embed = discord.Embed()
        embed.set_author(
            name=api_result['deviation']['author']['username'],
            url=f"https://www.deviantart.com/{api_result['deviation']['author']['username']}",
            icon_url=api_result['deviation']['author']['usericon'])
        embed.set_image(url=image_url)
        embed.set_footer(
            text=self.bot.assets['deviantart']['name'],
            icon_url=self.bot.assets['deviantart']['favicon'])

        await channel.send(embed=embed)

    async def get_imgur_gallery(self, msg, url):
        """Automatically fetch and post any image galleries from imgur"""

        channel = msg.channel

        album_id = utils.posts.get_post_id(url, ['/a/', '/gallery/'], '?')
        if not album_id:
            return

        search_url = self.bot.assets['imgur']['album_url'].format(album_id)
        api_result = (await utils.net.http_request(search_url, headers=self.bot.assets['imgur']['headers'], json=True)).json

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
