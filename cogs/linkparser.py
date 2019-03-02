import re

from discord.ext import commands


class LinkParserCog(commands.Cog, name="Owner Commands"):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx):
        """Test for image urls"""

        urls = self.get_urls(ctx.content)
        if urls:
            domains = self.get_domains(urls)
            for i, domain in enumerate(domains):
                if 'twitter.com' in domain:
                    print('twitter link')
                    # await get_twitter_gallery(msg, urls[i])

                if 'pixiv.net' in domain:
                    print('pixiv link')
                    # await get_pixiv_gallery(msg, urls[i])

    def get_urls(self, string):
        # findall() has been used
        # with valid conditions for urls in string
        regex_exp = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'  # pylint: disable=anomalous-backslash-in-string
        matching_urls = re.findall(regex_exp, string)
        return matching_urls

    def get_domains(self, array):
        domains = []

        for url in array:
            # thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
            domain = url.split('//')[-1].split('/')[0].split('?')[0]
            domains.append(domain)
        return domains


def setup(bot):
    bot.add_cog(LinkParserCog(bot))
