import datetime
import html

import discord
import tweepy

import koabot.core.posts as post_core
from koabot.core.embed import EmbedGroup
from koabot.core.previews import SitePreview
from koabot.kbot import KBot


class TwitterPreview(SitePreview):
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


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(TwitterPreview(bot))
