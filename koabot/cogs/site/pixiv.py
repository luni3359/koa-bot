import re
import shutil
from io import BytesIO
from pathlib import Path

import discord
import pixivpy_async

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.core.base import Site
from koabot.kbot import KBot
from koabot.patterns import HTML_TAG_OR_ENTITY_PATTERN


class PixivHelper():
    def __init__(self) -> None:
        self.files: list[discord.File] = []
        self.embeds: list[discord.Embed] = []

    def add_file(self, fp: BytesIO | str, filename: str) -> None:
        self.files.append(discord.File(fp=fp, filename=filename))

    def add_embed(self, embed: discord.Embed) -> None:
        self.embeds.append(embed)


class SitePixiv(Site):
    """Pixiv operations handler"""

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

    def get_post_url(self, post_id: str) -> str:
        return f"https://www.pixiv.net/artworks/{post_id}"

    def get_user_url(self, user_id: str) -> str:
        return f"https://www.pixiv.net/users/{user_id}"

    async def nsfw_check(self, msg: discord.Message, illust):
        """Checks if the process should continue depending on the content
        and channel it was posted on."""
        botstatus_cog = self.botstatus

        if illust.x_restrict != 0 and not msg.channel.is_nsfw():
            embed = discord.Embed()

            if 'nsfw_placeholder' in self.bot.assets['pixiv']:
                embed.set_image(url=self.bot.assets['pixiv']['nsfw_placeholder'])
            else:
                embed.set_image(url=self.bot.assets['default']['nsfw_placeholder'])

            content = f"{msg.author.mention} {botstatus_cog.get_quote('improper_content_reminder')}"
            await botstatus_cog.typing_a_message(msg.channel, content=content, embed=embed, rnd_duration=[1, 2])
            return True
        return False

    async def cache_image(self, url: str, filename: str, pixiv_helper: PixivHelper) -> None:
        # create if pixiv cache directory if it doesn't exist
        file_cache_dir = Path(self.bot.CACHE_DIR, "pixiv", "files")
        file_cache_dir.mkdir(exist_ok=True)
        image_path = Path(file_cache_dir, filename)

        image_bytes = None
        if not image_path.exists():
            print("Saving to cache...")
            image_bytes = await net_core.fetch_image(url, headers=self.bot.assets['pixiv']['headers'])

            with open(image_path, 'wb') as image_file:
                shutil.copyfileobj(image_bytes, image_file)
            image_bytes.seek(0)

        if image_bytes:
            pixiv_helper.add_file(image_bytes, filename)
            image_bytes.close()
        else:
            print("Uploading from cache...")
            pixiv_helper.add_file(image_path, filename)

    async def get_pixiv_gallery(self, msg: discord.Message, url: str, /, *, only_if_missing: bool = False) -> None:
        """Automatically fetch and post any image galleries from pixiv
        Arguments:
            msg::discord.Message
                The message where the link was sent
            url::str
                Link of the pixiv post
            only_if_missing::bool
                Only shows a preview if the native embed is missing from the original link. Default is False
        """
        if not (post_id := self.get_id(url)):
            return

        print(f"Now starting to process pixiv #{post_id}")
        url = self.get_post_url(post_id)

        # Login
        await self.reauthenticate_pixiv()

        try:
            illust_json = await self.pixiv_aapi.illust_detail(post_id, req_auth=True)
        except pixivpy_async.PixivError as e:
            await msg.channel.send("Odd...")
            return print(e)

        if 'illust' not in illust_json:
            return print(f"Invalid Pixiv id #{post_id}")

        print(f"Pixiv auth passed! (for #{post_id})")

        illust = illust_json.illust

        # if await self.nsfw_check(msg, illust):
        #     return

        async with msg.channel.typing():
            total_illust_pictures = illust.page_count
            pictures = illust.meta_pages if total_illust_pictures > 1 else [illust]
            total_to_preview = 1 if only_if_missing else 5

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
                                     url=self.get_user_url(illust.user.id))

                    # Thanks Pixiv... even your avatars are inaccessible!
                    # //////////////////////////////////////////////////////////////////
                    # avatar_url = illust.user.profile_image_urls.medium
                    # avatar_filename = net_core.get_url_filename(avatar_url)
                    # avatar_cache_dir = Path(self.bot.CACHE_DIR, 'pixiv', 'avatars')
                    # avatar_cache_dir.mkdir(exist_ok=True)
                    # avatar_path = Path(avatar_cache_dir, avatar_filename)

                    # # cache file if it doesn't exist
                    # image_bytes = None
                    # if not avatar_path.exists():
                    #     print('Saving to cache...')
                    #     image_bytes = await net_core.fetch_image(avatar_url, headers=self.bot.assets['pixiv']['headers'])

                    #     with open(avatar_path, 'wb') as image_file:
                    #         shutil.copyfileobj(image_bytes, image_file)
                    #     image_bytes.seek(0)

                # cache file if it doesn't exist
                await self.cache_image(img_url, filename, pixiv_helper)

                if i + 1 >= min(total_to_preview, total_illust_pictures):
                    if total_illust_pictures > total_to_preview:
                        remaining_footer = f"{total_illust_pictures - total_to_preview}+ remaining"
                    else:
                        remaining_footer = self.bot.assets['pixiv']['name']

                    embed.set_footer(
                        text=remaining_footer,
                        icon_url=self.bot.assets['pixiv']['favicon'])

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

        pixiv_cache_dir = Path(self.bot.CACHE_DIR, 'pixiv')
        token_filename = 'refresh_token'
        token_path = Path(pixiv_cache_dir, token_filename)

        if token_path.exists():
            with open(token_path, encoding="UTF-8") as token_file:
                self.pixiv_refresh_token = token_file.readline()
                await self.pixiv_aapi.login(refresh_token=self.pixiv_refresh_token)
        else:
            pix_keys = self.bot.auth_keys['pixiv']
            await self.pixiv_aapi.login(pix_keys['username'], pix_keys['password'])
            self.pixiv_refresh_token = self.pixiv_aapi.refresh_token
            pixiv_cache_dir.mkdir(exist_ok=True)
            with open(token_path, 'w', encoding="UTF-8") as token_file:
                token_file.write(self.pixiv_refresh_token)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SitePixiv(bot))
