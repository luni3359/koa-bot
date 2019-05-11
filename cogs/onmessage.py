import io
import random
import re
from datetime import datetime

import aiohttp
import discord
import pixivpy3
import tweepy
from discord.ext import commands


class OnMessageCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Twitter auth
        self.twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'], bot.auth_keys['twitter']['consumer_secret'])
        self.twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
        self.twitter_api = tweepy.API(self.twit_auth)

        # Pixiv auth
        self.pixiv_api = pixivpy3.AppPixivAPI()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Process message content"""
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        # Test for image urls
        urls = self.get_urls(message.content)
        if urls:
            domains = self.get_domains(urls)
            for i, domain in enumerate(domains):
                if self.bot.assets['twitter']['domain'] in domain:
                    print('twitter link')
                    await self.get_twitter_gallery(message, urls[i])

                if self.bot.assets['pixiv']['domain'] in domain:
                    print('pixiv link')
                    await self.get_pixiv_gallery(message, urls[i])

    async def get_twitter_gallery(self, msg, url):
        """Process twitter links"""
        channel = msg.channel

        post_id = self.get_post_id(url, '/status/', '?')
        if not post_id:
            return

        tweet = self.twitter_api.get_status(post_id, tweet_mode='extended')

        if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
            print('Preview gallery not applicable.')
            return

        print(msg.embeds)
        for e in msg.embeds:
            print(str(datetime.now()))
            print(dir(e))
            print(e.url)

        if not msg.embeds:
            print('I wouldn\'t have worked. Embeds report as 0 on the first try after inactivity on message #%i at %s.' % (msg.id, str(datetime.now())))
            # await channel.send('I wouldn't have worked')

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
                url='https://twitter.com/%s' % tweet.author.screen_name,
                icon_url=tweet.author.profile_image_url_https
            )
            embed.set_image(url=picture)

            # If it's the last picture to show, add a brand footer
            if total_gallery_pics <= 0:
                embed.set_footer(
                    text=self.bot.assets['twitter']['name'],
                    icon_url=self.bot.assets['twitter']['favicon']
                )

            await channel.send(embed=embed)

    async def get_pixiv_gallery(self, msg, url):
        """Process pixiv links"""
        channel = msg.channel

        post_id = self.get_post_id(url, 'illust_id=', '&')
        if not post_id:
            return

        print('Now starting to process pixiv link #%s' % post_id)
        if self.pixiv_api.access_token is None:
            self.pixiv_api.login(self.bot.auth_keys['pixiv']['username'], self.bot.auth_keys['pixiv']['password'])

        illust_json = self.pixiv_api.illust_detail(post_id, req_auth=True)
        print(illust_json)
        if 'error' in illust_json:
            # Attempt to login
            self.pixiv_api.login(self.bot.auth_keys['pixiv']['username'], self.bot.auth_keys['pixiv']['password'])
            illust_json = self.pixiv_api.illust_detail(post_id, req_auth=True)
            print(illust_json)

            if 'error' in illust_json:
                # too bad
                print('Invalid Pixiv id #%s' % post_id)
                return

        print('Pixiv auth passed! (for #%s)' % post_id)

        illust = illust_json.illust
        meta_dir = None

        if illust['meta_single_page']:
            meta_dir = 'meta_single_page'
        elif illust['meta_pages']:
            meta_dir = 'meta_pages'
        else:
            await channel.send('Sorry, sorry, sorry! Link missing data!')
            return

        total_illust_pictures = len(illust[meta_dir])
        if total_illust_pictures <= 1:
            illust[meta_dir] = [illust[meta_dir]]

        temp_wait = await channel.send('***%s***' % random.choice(self.bot.quotes['processing_long_task']))
        async with channel.typing():
            pictures_processed = 0
            for picture in illust[meta_dir][0:4]:
                pictures_processed += 1
                print('Retrieving picture from #%s...' % post_id)

                try:
                    img_url = picture.image_urls['medium']
                except AttributeError:
                    img_url = illust.image_urls['medium']

                image = await self.fetch_image(img_url, {'Referer': 'https://app-api.pixiv.net/'})

                print('Retrieved more from #%s (maybe)' % post_id)
                image_filename = self.get_file_name(img_url)
                embed = discord.Embed()
                embed.set_author(
                    name=illust['user']['name'],
                    url='https://www.pixiv.net/member.php?id=%i' % illust['user']['id']
                )
                embed.set_image(url='attachment://%s' % image_filename)

                if pictures_processed >= min(4, total_illust_pictures):
                    if total_illust_pictures > 4:
                        embed.set_footer(
                            text='%i+ remaining' % (total_illust_pictures - 4),
                            icon_url=self.bot.assets['pixiv']['favicon']
                        )
                    else:
                        embed.set_footer(
                            text=self.bot.assets['pixiv']['name'],
                            icon_url=self.bot.assets['pixiv']['favicon']
                        )

                await channel.send(file=discord.File(fp=image, filename=image_filename), embed=embed)

        await temp_wait.delete()
        print('DONE PIXIV!')

    # Following methods are use to parse strings
    async def fetch_image(self, url, headers={}):
        """Download image from url to memory"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                img_bytes = io.BytesIO(await response.read())
                return img_bytes

    @staticmethod
    def get_file_name(url):
        """Get filename from url"""
        return url.split('/')[-1]

    @staticmethod
    def get_post_id(url, word_to_match, trim_to):
        """Get post id from url"""
        if not word_to_match in url:
            return False

        return url.split(word_to_match)[1].split(trim_to)[0]

    # Following two static methods are used for parsing links
    @staticmethod
    def get_urls(message: str):
        """Get all urls from a given string"""

        url_pattern = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        matching_urls = re.findall(url_pattern, message)
        return matching_urls

    @staticmethod
    def get_domains(urls: list):
        """Get a list of domains from a list of strings
        https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868"""

        domains = []

        for url in urls:
            domain = url.split('//')[-1].split('/')[0].split('?')[0]
            domains.append(domain)
        return domains


def setup(bot):
    """Setup bot"""
    bot.add_cog(OnMessageCog(bot))
