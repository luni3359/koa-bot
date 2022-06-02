import asyncpraw
import discord
from asyncpraw.reddit import Submission, Subreddit

import koabot.core.posts as post_core
from koabot.core.base import Site
from koabot.kbot import KBot


class SiteReddit(Site):
    """Reddit operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self._reddit_api: asyncpraw.Reddit = None

    @property
    def reddit_api(self) -> asyncpraw.Reddit:
        if self._reddit_api:
            return self._reddit_api

        credentials = self.bot.auth_keys['reddit']
        self._reddit_api = asyncpraw.Reddit(client_id=credentials['client_id'],
                                            client_secret=credentials['client_secret'],
                                            username=credentials['username'],
                                            password=credentials['password'],
                                            user_agent=credentials['headers']['User-Agent'])
        return self._reddit_api

    async def cog_unload(self) -> None:
        print(f"Safely closing {self.qualified_name}")
        await self.reddit_api.close()
        return await super().cog_unload()

    def submission_is_video(self, submission: Submission):
        is_video = False
        if submission.is_video:
            is_video = True
            print("Preview preview not applicable. (reddit hosted video)")
        elif hasattr(submission, 'post_hint'):
            match submission.post_hint:
                case "hosted:video":
                    is_video = True
                    print("Preview preview not applicable. (reddit hosted video)")
                case "rich:video":
                    is_video = True
                    print("Preview preview not applicable. (rich video)")
        return is_video

    def get_subreddit_icon(self, subreddit: Subreddit):
        return subreddit.community_icon if subreddit.community_icon else subreddit.icon_img

    async def get_post(self, url: str) -> Submission:
        id_start = "comments/"
        id_end = "/"

        if not (post_id := post_core.get_name_or_id(url, start=id_start, end=id_end)):
            return None

        submission: Submission = await self.reddit_api.submission(id=post_id)

        # Don't override videos
        if self.submission_is_video(submission):
            return None

        return submission

    async def get_subreddit(self, url: str) -> Subreddit:
        id_start = "/r/"
        id_end = "/"

        if not (subreddit_name := post_core.get_name_or_id(url, start=id_start, end=id_end)):
            return None

        return await self.reddit_api.subreddit(display_name=subreddit_name)

    async def get_reddit_gallery(self, msg: discord.Message, url: str, /, *, guide: dict):
        """Automatically post Reddit galleries whenever possible"""
        if (post := await self.get_post(url)):
            await self.preview_submission(msg, post, guide)
        elif (subreddit := await self.get_subreddit(url)):
            await self.preview_subreddit(msg, subreddit, guide)

    async def preview_submission(self, msg: discord.Message, submission: Submission, guide: dict):
        subreddit: Subreddit = submission.subreddit
        await subreddit.load()

        header_embed = discord.Embed()
        header_embed.set_author(name=submission.subreddit_name_prefixed,
                                url=f"{guide['post']['url']}/{submission.subreddit_name_prefixed}",
                                icon_url=self.get_subreddit_icon(subreddit))
        header_embed.title = submission.title
        header_embed.url = f"{guide['post']['url']}{submission.permalink}"
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

    async def preview_subreddit(self, msg: discord.Message, subreddit: Subreddit, guide: dict):
        await subreddit.load()
        subreddit_url = f"{guide['post']['url']}/{subreddit.display_name_prefixed}"

        embed = discord.Embed()
        embed.set_author(name=subreddit.display_name_prefixed,
                                url=subreddit_url,
                                icon_url=self.get_subreddit_icon(subreddit))
        embed.title = subreddit.display_name
        embed.url = subreddit_url
        embed.description = subreddit.public_description
        embed.add_field(name='Members', value=f"{subreddit.subscribers:,}")
        embed.add_field(name='Online', value=f"{subreddit.active_user_count:,}")
        embed.set_footer(text=guide['embed']['footer_text'], icon_url=guide['embed']['favicon']['size192'])

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


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteReddit(bot))
