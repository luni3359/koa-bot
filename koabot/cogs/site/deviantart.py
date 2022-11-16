from http.cookies import SimpleCookie
import re

import discord
from thefuzz import fuzz

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.core import utils
from koabot.core.site import Site
from koabot.kbot import KBot
import aiohttp


class SiteDeviantArt(Site):
    """DeviantArt operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.csrf_token: str = None
        self.cookies: SimpleCookie = None

    async def get_csrf_token(self) -> str:
        if not self.csrf_token:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.deviantart.com") as response:
                    content = await response.text()
                    csrf_token = re.findall(r"window\.__CSRF_TOKEN__\ ?=\ ?'(\S+)';", content)
                    self.cookies = response.cookies

                    if not csrf_token:
                        raise Exception("Skipping preview: Unable to retrieve DA csrf token")

                    self.csrf_token = csrf_token[0]
                    print(f"DA success:\ncsrf token:{self.csrf_token}\ncookies:{self.cookies}")

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

        # TODO: Implement oEmbed if it looks possible! json responses are extremely shorter!
        # search_url = f"https://backend.deviantart.com/oembed?url={post_id}"

        # TODO: formerly
        # "search_url": "https://www.deviantart.com/_napi/da-deviation/shared_api/deviation/fetch?deviationid={}&type=art",
        # "search_url_extended": "https://www.deviantart.com/_napi/da-deviation/shared_api/deviation/extended_fetch?deviationid={}&type=art"

        search_url = self.bot.assets['deviantart']['search_url_extended']
        params = {
            "type": "art",
            "deviationid": post_id,
            "csrf_token": await self.get_csrf_token()
        }
        err_msg = f"Error fetching DA post #{post_id}"
        api_result = (await net_core.http_request(search_url, cookies=self.cookies, params=params, json=True, err_msg=err_msg)).json

        deviation = api_result['deviation']

        match (deviation_type := deviation['type']):
            case 'image' | 'literature' | 'pdf':
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
        MAX_EMBEDS = 5
        title_to_test_against = urls[0].split('/')[-1].rsplit('-', maxsplit=1)[0]
        similarity_ratio = 0
        for url in urls[1:]:
            title = url.split('/')[-1].rsplit('-', maxsplit=1)[0]
            similarity_ratio += fuzz.ratio(title, title_to_test_against)
            print(f"{title}: {title_to_test_against} ({fuzz.ratio(title, title_to_test_against)})")

        display_as_singles = False
        similarity_ratio /= len(urls) - 1
        print(f"Url similarity ratio: {similarity_ratio}")
        if similarity_ratio < 90:
            print("Urls seem unrelated from each other. Sending each embed individually.")
            display_as_singles = True

        # Check what type the first post is and if subsequent posts are of different types,
        # send them in one batch, but using different embed groups
        base_type: str = None
        api_results = []
        for url in urls:
            if not (post_id := self.get_id(url)):
                return

            search_url = self.bot.assets['deviantart']['search_url_extended']
            params = {
                "type": "art",
                "deviationid": post_id,
                "csrf_token": await self.get_csrf_token()
            }
            err_msg = f"Error fetching DA post #{post_id}"
            api_result = (await net_core.http_request(search_url, cookies=self.cookies, params=params, json=True, err_msg=err_msg)).json

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
        last_embed_index = min(MAX_EMBEDS - 1, total_da_count - 1)
        for i, deviation in enumerate([d['deviation'] for d in api_results[:MAX_EMBEDS]]):
            if display_as_singles:
                embed = self.build_deviantart_embed(urls[i], deviation)
                embeds.append(embed)
                continue
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
                if total_da_count > MAX_EMBEDS:
                    embed.set_footer(text=f"{total_da_count - MAX_EMBEDS}+ remaining", icon_url=embed.footer.icon_url)

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
                        case "gif" if "gif" in valid_types:
                            valid_types = valid_types[:valid_types.index("gif")]
                            image_url = media_type['b']
                        case "preview" if "preview" in valid_types:
                            valid_types = valid_types[:valid_types.index("preview")]
                            preview_url = media_type['c'].replace('<prettyName>', pretty_name)
                            preview_url = preview_url.replace(',q_80', ',q_100')
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
                embed.description = self.get_description_from_html(html_description, max_length=None) + "..."
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
