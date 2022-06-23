import discord
from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.cogs.handler.events import BotEvents
from koabot.kbot import KBot
from koabot.patterns import CHANNEL_URL_PATTERN


class PreviewHandler(commands.Cog):

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        # self.supported_sites: list[SitePreview] = [
        #     ""
        # ]

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def botevents(self) -> BotEvents:
        return self.bot.get_cog('BotEvents')

    # @staticmethod
    # def load_sites():
    #     pass

    # def get_preview(url):
    #     pass

    @commands.command(hidden=True)
    @commands.is_owner()
    async def preview(self, ctx: commands.Context, *, message_url: str):
        """Manually creates a preview from a given message url.
        It doesn't check for previously existing previews and is intended to be used
        exclusively by server staff (probably)"""
        if not (url_matches := CHANNEL_URL_PATTERN.match(message_url)):
            return await ctx.reply(self.botstatus.get_quote('rr_assign_missing_or_invalid_message_url'), mention_author=False)

        url_components = url_matches.group(0).split('/')
        message_id: int = int(url_components[-1])
        channel_id: int = int(url_components[-2])
        server_id: int = int(url_components[-3])

        if server_id != ctx.guild.id:
            return await ctx.reply("I can't preview messages from other servers!", mention_author=False)

        if channel_id != ctx.channel.id:
            target_channel = self.bot.get_channel(channel_id)
        else:
            target_channel = ctx.channel

        message: discord.Message = None
        try:
            message = await target_channel.fetch_message(message_id)
        except discord.NotFound:
            error_message = self.botstatus.get_quote('rr_assign_message_url_not_found')
        except discord.Forbidden:
            error_message = "I don't have permissions to interact with that message..."
        except discord.HTTPException:
            error_message = "Network issues. Please try again in a few moments."

        if not message:
            return await ctx.reply(error_message, mention_author=False)

        botevents = self.botevents
        url_matches_found = botevents.find_urls(message.content)
        prefix_start = False

        if (parsed_galleries := await botevents.parse_galleries(message, url_matches_found, prefix_start)):
            await botevents.send_previews(message, parsed_galleries, not prefix_start)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(PreviewHandler(bot))
