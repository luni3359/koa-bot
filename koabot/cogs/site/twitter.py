import html

import discord
import tweepy
import tweepy.asynchronous

import koabot.core.posts as post_core
from koabot.core.base import Site
from koabot.core.embed import EmbedGroup
from koabot.kbot import KBot


class SiteTwitter(Site):
    """Twitter operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self._twitter_api: tweepy.asynchronous.AsyncClient = None

    @property
    def twitter_api(self) -> tweepy.asynchronous.AsyncClient:
        if not self._twitter_api:
            twit_keys = self.bot.auth_keys['twitter']
            self._twitter_api = tweepy.asynchronous.AsyncClient(
                bearer_token=twit_keys['bearer_token'],
                consumer_key=twit_keys['consumer_key'],
                consumer_secret=twit_keys['consumer_secret'],
                access_token=twit_keys['access_token'],
                access_token_secret=twit_keys['access_token_secret'],
                wait_on_rate_limit=True)

        return self._twitter_api

    def get_id(self, guide: dict, url: str) -> str:
        id_start = guide['post']['id_start']
        id_end = guide['post']['id_end']

        return post_core.get_name_or_id(url, start=id_start, end=id_end)

    async def get_tweet(self, tweet_id) -> tweepy.Tweet:
        try:
            expansions = ["referenced_tweets.id", "attachments.media_keys", "author_id"]
            tweet_fields = ["possibly_sensitive", "public_metrics", "created_at", "entities"]
            return await self.twitter_api.get_tweet(tweet_id,
                                                    expansions=expansions,
                                                    tweet_fields=tweet_fields,
                                                    media_fields=["url", "preview_image_url", "alt_text"],
                                                    user_fields=["profile_image_url"])
        except tweepy.HTTPException as e:
            # Error codes: https://developer.twitter.com/en/support/twitter-api/error-troubleshooting
            print(f"Failure on Tweet #{tweet_id}\n{e}")
        return None

    async def check_applicable_tweet(self, msg: discord.Message, guide: dict, url: str, tweet: tweepy.Response):
        if not 'media' in tweet.includes:
            print("Twitter preview not applicable. (No media)")
            return False

        if len((tweet_media := tweet.includes['media'])) == 1:
            match tweet_media[0]['type']:
                case 'photo':
                    if not hasattr(tweet.data, 'possibly_sensitive') or not tweet.data.possibly_sensitive:
                        print("Twitter preview not applicable. (Media is sfw)")
                        return False

                    # TODO: There's got to be a better way...
                    if guide['embed']['footer_text'] == "TwitFix":
                        print("Twitter preview not applicable. (Handled by TwitFix)")
                        return False

                case _:  # 'video' or 'animated_gif'
                    if guide['embed']['footer_text'] == "TwitFix":
                        print("Twitter preview not applicable. (Handled by TwitFix)")

                    if hasattr(tweet.data, 'possibly_sensitive') and tweet.data.possibly_sensitive:
                        fixed_url = url.replace("twitter", "fxtwitter", 1)
                        await msg.reply(content=fixed_url, mention_author=False)
                    return False
        return True

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

        if not (tweet := await self.get_tweet(post_id)):
            return

        if not await self.check_applicable_tweet(msg, guide, url, tweet):
            return

        # Appending :orig to get a better image quality
        gallery_pics = [f"{picture['url']}:orig" for picture in tweet.includes['media']]

        embed_group = EmbedGroup()
        embed_group.color = discord.Colour(int(guide['embed']['color'], 16))

        # If it's the first picture to show then add author, body, and counters
        tweet_author = tweet.includes['users'][0]
        embed_group.first.set_author(
            name=f'{tweet_author.name} (@{tweet_author.username})',
            url=guide['post']['url'].format(tweet_author.username),
            icon_url=tweet_author.profile_image_url)

        metrics = tweet.data.public_metrics
        if (tw_likes := metrics['like_count']) > 0:
            embed_group.first.add_field(name='Likes', value=f"{tw_likes:,}")
        if (tw_retweets := metrics['retweet_count']) > 0:
            embed_group.first.add_field(name='Retweets', value=f"{tw_retweets:,}")

        # range_start, range_end = tweet.display_text_range  # there doesn't seem to be any good alternative to this in the v2 API
        # https://twittercommunity.com/t/display-text-range-not-included-in-api-v2-tweet-lookup-or-statuses-user-timeline/161896
        embed_group.first.description = html.unescape(tweet.data.text[0:tweet.data.entities['urls'][-1]['start'] - 1])

        # If it's the last picture to show, add a brand footer
        embed_group.last.set_footer(
            text=guide['embed']['footer_text'] + " • Mobile-friendly viewer",
            icon_url=self.bot.assets['twitter']['favicon'])
        embed_group.last.timestamp = tweet.data.created_at

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


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteTwitter(bot))
