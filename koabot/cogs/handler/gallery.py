"""Handles the use of imageboard galleries"""
import os
import random
import typing

import appdirs
import discord
import pixivpy3
from discord.ext import commands

import koabot.koakuma
import koabot.utils.posts


class Gallery(commands.Cog):
    """Gallery class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def display_static(self, channel, msg, url, **kwargs):
        """Automatically automatic
        Keywords:
            board::str
                The board to handle. Default is 'danbooru'
            id_start::str
                The point at which an url is stripped from
            id_end::str
                The point at which an url is stripped to
            end_regex::bool
                Whether or not id_end is regex. Default is False
        """

        board = kwargs.get('board', 'danbooru')
        id_start = kwargs.get('id_start')
        id_end = kwargs.get('id_end')
        end_regex = kwargs.get('end_regex', False)

        on_nsfw_channel = channel.is_nsfw()
        post_id = koabot.utils.posts.get_post_id(url, id_start, id_end, has_regex=end_regex)

        if not post_id:
            return

        bot_cog = self.bot.get_cog('BotStatus')
        board_cog = self.bot.get_cog('Board')

        if bot_cog is None:
            print('BOTSTATUS COG WAS MISSING!')
        if board_cog is None:
            print('BOARD COG WAS MISSING!')

        post = await board_cog.search_query(board=board, post_id=post_id)

        if not post:
            return

        if 'post' in post:
            post = post['post']

        if post['rating'] is not 's' and not on_nsfw_channel:
            embed = discord.Embed()
            if 'nsfw_placeholder' in self.bot.assets[board]:
                embed.set_image(url=self.bot.assets[board]['nsfw_placeholder'])
            else:
                embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            content = '%s %s' % (msg.author.mention, random.choice(self.bot.quotes['improper_content_reminder']))

            await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

        single_post = False
        if board == 'e621':
            if post['relationships']['has_active_children']:
                search = 'parent:%s order:id' % post['id']
            elif post['relationships']['parent_id']:
                search = [
                    'id:%s' % post['relationships']['parent_id'],
                    'parent:%s order:id -id:%s' % (post['relationships']['parent_id'], post['id'])
                ]
            else:
                single_post = True
        else:
            if post['has_children']:
                search = 'parent:%s order:id -id:%s' % (post['id'], post['id'])
            elif post['parent_id']:
                search = 'parent:%s order:id -id:%s' % (post['parent_id'], post['id'])
            else:
                single_post = True

        if single_post:
            if koabot.utils.posts.post_is_missing_preview(post, board=board):
                if post['rating'] is 's' or on_nsfw_channel:
                    await board_cog.send_posts(channel, post, board=board)
            return

        # If there's multiple searches, put them all in the posts list
        if isinstance(search, typing.List):
            posts = []
            for query in search:
                results = await board_cog.search_query(board=board, tags=query, include_nsfw=on_nsfw_channel)
                posts.extend(results['posts'])
        else:
            posts = await board_cog.search_query(board=board, tags=search, include_nsfw=on_nsfw_channel)

        # e621 fix for broken API
        if 'posts' in posts:
            posts = posts['posts']

        # Rudimentary fix when NSFW results are returned and it's a safe channel (should actually revert at some point)
        # Ought to respect the choice to display posts anyway but without thumbnail
        if not on_nsfw_channel:
            # filters all safe results into the posts variable
            posts = [post for post in posts if post['rating'] is 's']

        post_included_in_results = False
        if koabot.utils.posts.post_is_missing_preview(post, board=board) and posts:
            if post['rating'] is 's' or on_nsfw_channel:
                post_included_in_results = True
                post = [post]
                post.extend(posts)
                posts = post

        if posts:
            if post_included_in_results:
                await board_cog.send_posts(channel, posts, board=board, show_nsfw=on_nsfw_channel, max_posts=5)
            else:
                await board_cog.send_posts(channel, posts, board=board, show_nsfw=on_nsfw_channel)
        else:
            if post['rating'] is 's':
                content = random.choice(self.bot.quotes['cannot_show_nsfw_gallery'])
            else:
                content = random.choice(self.bot.quotes['rude_cannot_show_nsfw_gallery'])

            await bot_cog.typing_a_message(channel, content=content, rnd_duration=[1, 2])

    async def get_twitter_gallery(self, msg, url):
        """Automatically fetch and post any image galleries from twitter"""

        channel = msg.channel

        post_id = koabot.utils.posts.get_post_id(url, '/status/', '?')
        if not post_id:
            return

        tweet = self.bot.twitter_api.get_status(post_id, tweet_mode='extended')

        if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
            print('Preview gallery not applicable.')
            return

        gallery_pics = []
        for picture in tweet.extended_entities['media'][1:]:
            if picture['type'] != 'photo':
                return

            # Appending :orig to get a better image quality
            gallery_pics.append(picture['media_url_https'] + ':orig')

        total_gallery_pics = len(gallery_pics)
        for picture in gallery_pics:
            total_gallery_pics -= 1

            embed = discord.Embed()
            embed.set_author(
                name='%s (@%s)' % (tweet.author.name, tweet.author.screen_name),
                url='https://twitter.com/' + tweet.author.screen_name,
                icon_url=tweet.author.profile_image_url_https)
            embed.set_image(url=picture)

            # If it's the last picture to show, add a brand footer
            if total_gallery_pics <= 0:
                embed.set_footer(
                    text=self.bot.assets['twitter']['name'],
                    icon_url=self.bot.assets['twitter']['favicon'])

            await channel.send(embed=embed)

    async def get_pixiv_gallery(self, msg, url):
        """Automatically fetch and post any image galleries from pixiv"""

        channel = msg.channel

        post_id = koabot.utils.posts.get_post_id(url, ['illust_id=', '/artworks/'], '&')
        if not post_id:
            return

        print('Now starting to process pixiv link #' + post_id)

        # Login
        if self.bot.pixiv_api.access_token is None:
            token_name = 'pixiv_refresh_token'
            token_dir = os.path.join(appdirs.user_cache_dir('koa-bot'), token_name)

            if hasattr(self.bot, token_name):
                self.bot.pixiv_api.auth(refresh_token=self.bot.pixiv_refresh_token)
            elif os.path.exists(token_dir):
                with open(token_dir) as token_file:
                    token = token_file.readline()
                    self.bot.pixiv_refresh_token = token
                    self.bot.pixiv_api.auth(refresh_token=token)
            else:
                self.bot.pixiv_api.login(self.bot.auth_keys['pixiv']['username'], self.bot.auth_keys['pixiv']['password'])
                self.bot.pixiv_refresh_token = self.bot.pixiv_api.refresh_token
                with open(token_dir, 'w') as token_file:
                    token_file.write(self.bot.pixiv_api.refresh_token)
        else:
            self.bot.pixiv_api.auth(refresh_token=self.bot.pixiv_refresh_token)

        try:
            illust_json = self.bot.pixiv_api.illust_detail(post_id, req_auth=True)
        except pixivpy3.PixivError as e:
            await channel.send('Odd...')
            print(e)
            return

        print(illust_json)
        if 'illust' not in illust_json:
            # too bad
            print('Invalid Pixiv id #' + post_id)
            return

        print('Pixiv auth passed! (for #%s)' % post_id)

        illust = illust_json.illust
        if illust.x_restrict != 0 and not channel.is_nsfw():
            embed = discord.Embed()

            if 'nsfw_placeholder' in self.bot.assets['pixiv']:
                embed.set_image(url=self.bot.assets['pixiv']['nsfw_placeholder'])
            else:
                embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            content = '%s %s' % (msg.author.mention, random.choice(self.bot.quotes['improper_content_reminder']))

            bot_cog = self.bot.get_cog('BotStatus')

            if bot_cog is None:
                print('BOTSTATUS COG WAS MISSING!')

            await bot_cog.typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])
            return

        temp_message = await channel.send('***%s***' % random.choice(self.bot.quotes['processing_long_task']))
        async with channel.typing():
            total_illust_pictures = illust.page_count

            if total_illust_pictures > 1:
                pictures = illust.meta_pages
            else:
                pictures = [illust]

            pictures_processed = 0
            for picture in pictures[:4]:
                pictures_processed += 1
                print('Retrieving picture from #%s...' % post_id)

                (embed, image, filename) = await generate_pixiv_embed(picture, illust.user)
                print('Retrieved more from #%s (maybe)' % post_id)

                if pictures_processed >= min(4, total_illust_pictures):
                    remaining_footer = ''

                    if total_illust_pictures > 4:
                        remaining_footer = '%i+ remaining' % (total_illust_pictures - 4)
                    else:
                        remaining_footer = self.bot.assets['pixiv']['name']

                    embed.set_footer(
                        text=remaining_footer,
                        icon_url=self.bot.assets['pixiv']['favicon'])
                await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)

        await temp_message.delete()
        print('DONE PIXIV!')

    async def get_sankaku_post(self, msg, url):
        """Automatically fetch a bigger preview from Sankaku Complex"""

        channel = msg.channel

        post_id = koabot.utils.posts.get_post_id(url, '/show/', '?')
        if not post_id:
            return

        search_url = self.bot.assets['sankaku']['id_search_url'] + post_id
        api_result = await koabot.utils.net.http_request(search_url, json=True)

        if not api_result or 'code' in api_result:
            print('Sankaku error\nCode #%s' % api_result['code'])
            return

        embed = discord.Embed()
        embed.set_image(url=api_result['preview_url'])
        embed.set_footer(
            text=self.bot.assets['sankaku']['name'],
            icon_url=self.bot.assets['sankaku']['favicon'])

        await channel.send(embed=embed)

    async def get_deviantart_post(self, msg, url):
        """Automatically fetch post from deviantart"""

        channel = msg.channel

        post_id = koabot.utils.posts.get_post_id(url, '/art/', r'[0-9]+$', has_regex=True)
        if not post_id:
            return

        search_url = self.bot.assets['deviantart']['search_url_extended'].format(post_id)

        api_result = await koabot.utils.net.http_request(search_url, json=True, err_msg='error fetching post #' + post_id)

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

        image_url = '%s/%s?token=%s' % (baseUri, preview_url, token)
        print(image_url)

        embed = discord.Embed()
        embed.set_author(
            name=api_result['deviation']['author']['username'],
            url='https://www.deviantart.com/' + api_result['deviation']['author']['username'],
            icon_url=api_result['deviation']['author']['usericon'])
        embed.set_image(url=image_url)
        embed.set_footer(
            text=self.bot.assets['deviantart']['name'],
            icon_url=self.bot.assets['deviantart']['favicon'])

        await channel.send(embed=embed)

    async def get_imgur_gallery(self, msg, url):
        """Automatically fetch and post any image galleries from imgur"""

        channel = msg.channel

        album_id = koabot.utils.posts.get_post_id(url, ['/a/', '/gallery/'], '?')
        if not album_id:
            return

        search_url = self.bot.assets['imgur']['album_url'].format(album_id)
        api_result = await koabot.utils.net.http_request(search_url, headers=self.bot.assets['imgur']['headers'], json=True)

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
                    remaining_footer = '%i+ remaining' % (total_album_pictures - 4)
                else:
                    remaining_footer = self.bot.assets['imgur']['name']

                embed.set_footer(
                    text=remaining_footer,
                    icon_url=self.bot.assets['imgur']['favicon']['size32'])

            await channel.send(embed=embed)


async def generate_pixiv_embed(post, user):
    """Generate embeds for pixiv urls
    Arguments:
        post
            The post object
        user
            The artist of the post
    """

    img_url = post.image_urls.medium
    image_filename = koabot.utils.net.get_url_filename(img_url)
    image = await koabot.utils.net.fetch_image(img_url, headers=koabot.koakuma.bot.assets['pixiv']['headers'])

    embed = discord.Embed()
    embed.set_author(
        name=user.name,
        url='https://www.pixiv.net/member.php?id=%i' % user.id)
    embed.set_image(url='attachment://' + image_filename)
    return embed, image, image_filename


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Gallery(bot))
