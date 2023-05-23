import re
from pathlib import Path

import aiohttp
import discord
from thefuzz import fuzz

import koabot.core.posts as post_core
from koabot.core import utils
from koabot.core.site import Site
from koabot.kbot import KBot


class SiteDeviantArt(Site):
    """DeviantArt operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.csrf_token: str = None
        self.cookies: aiohttp.CookieJar = None
        self.cache_dir = Path(self.bot.CACHE_DIR, "deviantart")
        self.max_embeds = 5

    async def get_csrf_token(self) -> str:
        """Generates a new csrf token or retrieves a cached one"""
        if self.csrf_token:
            return self.csrf_token

        token_path = Path(self.cache_dir, "csrf_token")
        cookies_path = Path(self.cache_dir, "cookies")
        cookies = aiohttp.CookieJar()

        if token_path.exists():
            with open(token_path, encoding="UTF-8") as token_file:
                self.csrf_token = token_file.readline()

        if cookies_path.exists():
            cookies.load(cookies_path)
            self.cookies = cookies

        if not self.csrf_token or not self.cookies:
            self.cache_dir.mkdir(exist_ok=True)

            async with aiohttp.ClientSession(cookie_jar=cookies) as session:
                async with session.get("https://www.deviantart.com") as response:
                    content = await response.text()

                    if not (csrf_token := re.findall(r"window\.__CSRF_TOKEN__\ ?=\ ?'(\S+)';", content)):
                        raise Exception("Skipping preview: Unable to retrieve DA csrf token")

                    self.csrf_token = csrf_token[0]
                    with open(token_path, 'w', encoding="UTF-8") as token_file:
                        token_file.write(self.csrf_token)

                    self.cookies = cookies
                    cookies.save(cookies_path)

                    print(f"DA auth success:\ncsrf token:{self.csrf_token}\ncookies:{self.cookies}")

        return self.csrf_token

    def get_id(self, url: str) -> str:
        return post_core.get_name_or_id(url, start='/art/', pattern=r'[0-9]+$')

    def get_description_from_html(self, html_description: str, max_length: int = 200) -> str:
        description = utils.convert_code_points(html_description)
        description = utils.strip_html_markup(description).strip()

        # remove outgoing DA redirect
        description = re.sub(r'https?:\/\/(?:www\.)?deviantart\.com\/users\/outgoing\?', '', description)

        if max_length and len(description) > max_length:
            description = utils.smart_truncate(description, max_length, inclusive=True) + "..."
        return description

    async def get_deviantart_post(self, msg: discord.Message, url: str, /) -> None:
        """Automatically fetch post from deviantart"""

        if not (post_id := self.get_id(url)):
            return

        print(f"Sending DA post #{post_id}...")

        # TODO: Implement oEmbed if it looks possible! json responses are extremely shorter!
        # search_url = f"https://backend.deviantart.com/oembed?url={post_id}"

        # TODO: formerly
        # "search_url": "https://www.deviantart.com/_napi/da-deviation/shared_api/deviation/fetch?deviationid={}&type=art",
        # "search_url_extended": "https://www.deviantart.com/_napi/da-deviation/shared_api/deviation/extended_fetch?deviationid={}&type=art"

        # Get the csrf token first, otherwise the first request will fail (always)
        csrf_token = await self.get_csrf_token()

        search_url = self.bot.assets['deviantart']['search_url_extended']
        api_result = None
        async with aiohttp.ClientSession(cookie_jar=self.cookies) as session:
            params = {
                "type": "art",
                "deviationid": post_id,
                "csrf_token": csrf_token
            }
            async with session.get(search_url, params=params) as response:
                api_result = await response.json()

        if not api_result:
            print(f"Failed to retrieve DA post #{post_id}")
        elif 'error' in api_result:
            # {'error': 'invalid_request', 'errorDescription': 'Invalid or expired form submission', 'errorDetails': {'csrf': 'invalid'}, 'status': 'error'}
            print(f"{api_result['error']}: {api_result['errorDescription']}\n{api_result['errorDetails']}")

        deviation = api_result['deviation']

        match (deviation_type := deviation['type']):
            case 'image' | 'literature' | 'pdf':
                embed = self.build_deviantart_embed(url, deviation)
            case _:
                print(f"Incapable of handling DeviantArt url (type: {deviation_type}):\n{url}")
                return

        await self.send_deviantart(msg, [embed])

    def get_title_from_url(self, url: str) -> str:
        """Returns the title present in a given DA url"""
        # TODO: This is not a reliable method because an url is not guaranteed to valid title in it
        return url.split('/')[-1].rsplit('-', maxsplit=1)[0]

    def url_similarity_ratio(self, urls: list[str]) -> float:
        """Calculate how similar a group of urls are from each other"""
        title_to_test_against = self.get_title_from_url(urls[0])
        similarity_ratio = 0
        for url in urls[1:]:
            title = self.get_title_from_url(url)
            similarity_ratio += fuzz.ratio(title, title_to_test_against)
            print(f"{title}: {title_to_test_against} ({fuzz.ratio(title, title_to_test_against)})")

        similarity_ratio /= len(urls) - 1
        print(f"Url similarity ratio: {similarity_ratio}")
        return similarity_ratio

    async def get_deviantart_posts(self, msg: discord.Message, urls: list[str]):
        """Automatically fetch multiple posts from deviantart"""
        display_as_singles = False
        if self.url_similarity_ratio(urls) < 90:
            print("Urls seem unrelated from each other. Sending each embed individually.")
            display_as_singles = True

        # Get the csrf token first, otherwise ClientSession will fail to create
        csrf_token = await self.get_csrf_token()

        # Check what type the first post is and if subsequent posts are of different types,
        # send them in one batch, but using different embed groups
        base_type: str = None
        search_url = self.bot.assets['deviantart']['search_url_extended']
        api_results = []
        async with aiohttp.ClientSession(cookie_jar=self.cookies) as session:
            for url in urls:
                if not (post_id := self.get_id(url)):
                    return

                api_result = None
                params = {
                    "type": "art",
                    "deviationid": post_id,
                    "csrf_token": csrf_token
                }
                async with session.get(search_url, params=params) as response:
                    api_result = await response.json()

                deviation = api_result['deviation']
                deviation_type = deviation['type']

                if base_type is None:
                    base_type = deviation_type

                if deviation_type != base_type:
                    print("Deviation types differ. Sending each embed individually.")
                    display_as_singles = True

                api_results.append(api_result)

        embeds: list[discord.Embed] = []
        total_da_count = len(api_results)
        last_embed_index = min(self.max_embeds, total_da_count) - 1
        deviations = [d['deviation'] for d in api_results[:self.max_embeds]]

        if display_as_singles:
            for i, deviation in enumerate(deviations):
                embeds.append(self.build_deviantart_embed(urls[i], deviation))
        else:
            for i, deviation in enumerate(deviations):
                url = urls[i]
                if i != last_embed_index:
                    if i == 0:
                        embed = self.build_deviantart_embed(url, deviation)
                        embed.remove_footer()
                    else:
                        embed = self.build_deviantart_embed(url, deviation, image_only=True)
                else:
                    # i == last_embed_index
                    embed = self.build_deviantart_embed(url, deviation)
                    embed.description = ""
                    embed.remove_author()
                    embed.clear_fields()
                    if total_da_count > self.max_embeds:
                        footer_text = f"{total_da_count - self.max_embeds}+ remaining"
                        embed.set_footer(text=footer_text, icon_url=embed.footer.icon_url)
                embeds.append(embed)

        await self.send_deviantart(msg, embeds)

    async def send_deviantart(self, msg: discord.Message, embeds: list[discord.Embed]):
        if len(embeds) > 1:
            await msg.reply(embeds=embeds, mention_author=False)
        else:
            await msg.reply(embed=embeds[0], mention_author=False)

        try:
            await msg.edit(suppress=True)
        except discord.errors.Forbidden:
            # Missing Permissions
            print("Missing Permissions: Cannot suppress embed from sender's message")

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
                        case "gif" if "gif" in valid_types:
                            valid_types = valid_types[:valid_types.index("gif")]
                            image_url = media_type['b']
                        case "preview" if "preview" in valid_types:
                            valid_types = valid_types[:valid_types.index("preview")]
                            preview_url = media_type['c'].replace("<prettyName>", pretty_name)
                            preview_url = preview_url.replace(",q_80", ",q_100")
                            image_url = f"{base_uri}{preview_url}"

                image_url = f"{image_url}?token={token}"

                if 'descriptionText' in deviation['extended'] and not image_only:
                    html_description = deviation['extended']['descriptionText']['html']['markup']
                    embed.description = self.get_description_from_html(html_description)

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

                if 'descriptionText' in deviation['extended'] and not image_only:
                    html_description = deviation['extended']['descriptionText']['html']['markup']
                    embed.description = self.get_description_from_html(html_description)

                embed.set_image(url=image_url)
            case 'literature':
                # DA's excerpts should be a maximum of ~650 characters by default, hence None
                # TODO: Check what happens with literature <650 long
                html_description = deviation['textContent']['excerpt']
                description = self.get_description_from_html(html_description, max_length=None)
                embed.description = f"{description}..."
            case 'pdf':
                if 'descriptionText' in deviation['extended']:
                    html_description = deviation['extended']['descriptionText']['html']['markup']
                    embed.description = self.get_description_from_html(html_description, max_length=650)
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


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteDeviantArt(bot))
