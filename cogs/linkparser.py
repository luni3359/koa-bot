import re

from discord.ext import commands


class LinkParserCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx):
        """Test for image urls"""

        urls = self.get_urls(ctx.content)
        if urls:
            domains = self.get_domains(urls)
            for i, domain in enumerate(domains):
                if self.bot.assets['twitter']['domain'] in domain:
                    print('twitter link')
                    # await get_twitter_gallery(msg, urls[i])

                if self.bot.assets['pixiv']['domain'] in domain:
                    print('pixiv link')
                    # await get_pixiv_gallery(msg, urls[i])

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
    bot.add_cog(LinkParserCog(bot))
