import discord

import koabot.core.net as net_core
import koabot.core.posts as post_core
from koabot.core.site import Site
from koabot.kbot import KBot


class SiteImgur(Site):
    """Imgur operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)

    async def get_imgur_gallery(self, msg: discord.Message, url: str):
        """Automatically fetch and post any image galleries from imgur"""
        if not (album_id := post_core.get_name_or_id(url, start=['/a/', '/gallery/'])):
            return

        search_url = self.bot.assets['imgur']['album_url'].format(album_id)
        api_result = (await net_core.http_request(search_url, headers=self.bot.assets['imgur']['headers'], json=True)).json

        if not api_result or api_result['status'] != 200:
            return

        # TODO: Why -1?
        if (total_album_pictures := len(api_result['data']) - 1) < 1:
            return

        embeds_to_send = []
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

            embeds_to_send.append(embed)

        await msg.reply(embeds=embeds_to_send, mention_author=False)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteImgur(bot))
