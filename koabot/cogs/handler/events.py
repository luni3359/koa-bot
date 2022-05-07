"""Bot events"""
import re
import sys
import traceback
from datetime import datetime

import discord
import tldextract
from discord.ext import commands
from mergedeep import merge

from koabot.cogs.botstatus import BotStatus
from koabot.cogs.imageboard import ImageBoard
from koabot.cogs.reactionroles import ReactionRoles
from koabot.cogs.streamservice import StreamService
from koabot.kbot import KBot
from koabot.patterns import COMMAND_PATTERN, URL_PATTERN


class UrlMatch():
    def __init__(self, full_url, fqdn) -> None:
        self.full_url: str = full_url
        self.fqdn: str = fqdn


class MatchGroup():
    def __init__(self, group, url, guide) -> None:
        self.url: str = url
        self.group: str = group
        self.guide: dict = guide


class BotEvents(commands.Cog):
    """BotEvents class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.bot.last_channel = 0
        self.bot.last_channel_warned = False
        self.bot.last_channel_message_count = 0
        self.beta_bot_id = self.bot.koa['discord_user']['beta_id']

        self.match_groups: list[MatchGroup] = []
        self.build_valid_urls()

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def imageboard(self) -> ImageBoard:
        return self.bot.get_cog('ImageBoard')

    @property
    def reactionroles(self) -> ReactionRoles:
        return self.bot.get_cog('ReactionRoles')

    @property
    def streamservice(self) -> StreamService:
        return self.bot.get_cog('StreamService')

    def build_valid_urls(self) -> None:
        """Guides stuff"""
        self.match_groups = []

        for group, contents in self.bot.match_groups.items():
            for match in contents:
                url_pattern = match['url']
                url_pattern = url_pattern.replace(r'.', r'\.')
                url_pattern = url_pattern.replace(r'*', r'(.*?)')
                self.match_groups.append(MatchGroup(group, url_pattern, match['guide']))

        for guide_type, v in self.bot.guides.items():
            for guide_name, guide_content in v.items():
                if 'inherits' not in guide_content:
                    continue

                guide_to_inherit = guide_content['inherits'].split('/')
                source_guide = self.bot.guides[guide_type][guide_name]

                if len(guide_to_inherit) > 1:
                    target_guide = self.bot.guides[guide_to_inherit[0]][guide_to_inherit[1]]
                else:
                    target_guide = self.bot.guides[guide_type][guide_to_inherit[0]]

                combined_guide = merge({}, target_guide, source_guide)
                self.bot.guides[guide_type][guide_name] = combined_guide

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """When a user adds a reaction to a message"""
        if payload.user_id == self.bot.user.id:
            return

        guild: discord.Guild = self.bot.get_guild(payload.guild_id)

        if payload.member:
            user = payload.member
        else:
            user: discord.abc.User = guild.get_member(payload.user_id)

        # might get false positives in the future... if the user isn't cached
        if user is None or user.bot:
            return

        await self.reactionroles.reaction_added(payload, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """When a user removes a reaction from a message"""
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)

        # might get false positives in the future... if the user isn't cached
        if user is None or user.bot:
            return

        await self.reactionroles.reaction_removed(payload, user)

    # TODO: General error handler: https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """
        if hasattr(ctx.command, 'on_error'):
            return

        # Temporarily disabled as this makes cog_command_error override this listener entirely
        # if cog := ctx.cog:
        #     if cog._get_overridden_method(cog.cog_command_error) is not None:
        #         return

        ignored = (commands.CommandNotFound, commands.CheckFailure, )
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == 'tag list':
                await ctx.send('I could not find that member. Please try again.')

        else:
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Make the embeds created by the bot unsuppressable"""
        if not before.author.bot:
            return

        if before.author != before.guild.me:
            return

        if len(before.embeds) > 0 and len(after.embeds) == 0:
            await after.edit(suppress=False)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Searches messages for urls and certain keywords"""
        author: discord.User | discord.Member = msg.author

        # Prevent bot from spamming itself
        if author.bot:
            return

        if msg.guild is None:
            print(f'{author.name}#{author.discriminator} ({author.id}): {msg.content}')
            return

        # Beta bot overrides me in the servers we share
        if self.beta_bot_override(author.id not in self.bot.testing['debug_users'], msg.guild):
            return

        botstatus_cog = self.botstatus
        empty_message = not bool(msg.content)

        if empty_message:
            return

        prefix_start = msg.content[0] == '!'

        # only create references if asked for
        if prefix_start and msg.channel_mentions:
            await self.create_channel_references(msg, msg.guild, author, botstatus_cog)

        url_matches_found = self.find_urls(msg.content)

        if (parsed_galleries := await self.parse_galleries(msg, url_matches_found, prefix_start)):
            await self.send_previews(msg, parsed_galleries, not prefix_start)

        # checking if a command has been issued
        if prefix_start:
            command_issued = self.command_was_issued(msg)
        else:
            command_issued = False

        await self.check_quiet_channels(msg, botstatus_cog, command_issued or url_matches_found)

    async def create_channel_references(self, msg: discord.Message, guild, author, botstatus_cog: BotStatus):
        """Reference channels together"""
        for target_chnl in msg.channel_mentions:
            if target_chnl == msg.channel:
                continue

            embed_template = discord.Embed()
            guild_icon_url = guild.icon.url if hasattr(guild, 'guild') else None
            embed_template.set_author(name=author.display_name, icon_url=author.avatar.url)
            embed_template.set_footer(text=guild.name, icon_url=guild_icon_url)

            target_embed = embed_template.copy()
            target_embed.description = botstatus_cog.get_quote(
                'channel_linking_target', author=author.mention, channel=msg.channel.mention, msg_url=msg.jump_url)
            target_chnl_msg = await target_chnl.send(embed=target_embed)

            origin_embed = embed_template.copy()
            target_chnl_mention = target_chnl.mention
            target_jmp_url = target_chnl_msg.jump_url
            origin_embed.description = botstatus_cog.get_quote(
                'channel_linking_origin', author=author.mention, channel=target_chnl_mention, msg_url=target_jmp_url)
            await msg.channel.send(embed=origin_embed)

    def beta_bot_override(self, not_beta_user: bool, guild: discord.Guild):
        """Checks if there's two separate instances of the same bot running on the same server, so that 
        only one of them can everrespond at a time. It's user-based, so only select users get to use 
        the beta when both are present. 
        """
        # if it's a normal user...
        if not_beta_user:
            # ...and i'm the debug instance
            if guild.me.id == self.beta_bot_id:
                # do nothing
                return True
            return False
        # or if it's a debug user...
        beta_bot: discord.Member = guild.get_member(self.beta_bot_id)
        # ...and the debug instance is online
        if beta_bot and beta_bot.status == discord.Status.online:
            # ...and i'm not the debug instance
            if guild.me.id != self.beta_bot_id:
                # do nothing
                return True
        return False

    def find_urls(self, string: str) -> list[UrlMatch]:
        """Finds all urls in a given string, ignoring those enclosed in <>"""
        url_matches = []
        escaping_url = False
        i = 0
        while i < len(string):
            # check for urls, ignoring those with escaped embeds
            if string[i] == '<':
                escaping_url = True
                i += 1
                continue

            if (url_match := URL_PATTERN.match(string, i)):
                url_match_end = url_match.end()
                end_of_string = url_match_end >= len(string)
                within_string = url_match_end < len(string)
                if not escaping_url or end_of_string or (within_string and string[url_match_end] != '>'):
                    full_url = url_match.group()
                    fqdn = tldextract.extract(url_match.group()).fqdn
                    url_matches.append(UrlMatch(full_url, fqdn))

                i = url_match_end
                continue

            escaping_url = False
            i += 1

        return url_matches

    async def parse_galleries(self, msg: discord.Message, url_matches: list[UrlMatch], delete_original) -> list[MatchGroup]:
        parsed_galleries = []
        for url_match in url_matches:
            for match_group in self.match_groups:
                # match() matches only from the start of the string
                if not re.match(match_group.url, url_match.fqdn):
                    continue

                for guide in match_group.guide:
                    guide_type = guide['type']
                    guide_name = guide['name']

                    try:
                        guide_content = self.bot.guides[guide_type][guide_name]
                    except KeyError as e:
                        print(f'KeyError: "{e.args[0]}" is an undefined guide name or type.')
                        continue

                    match guide_type:
                        case 'gallery':
                            parsed_galleries.append(MatchGroup(match_group.group, url_match.full_url, guide_content))
                        case 'stream' if match_group.group == 'picarto':
                            picarto_preview_shown = await self.streamservice.get_picarto_stream_preview(msg, url_match.full_url, orig_to_be_deleted=delete_original)

                            if picarto_preview_shown and delete_original:
                                await msg.delete()

                # done with this url
                break

        return parsed_galleries

    async def send_previews(self, msg: discord.Message, parsed_galleries: list[MatchGroup], only_if_missing: bool) -> None:
        # post gallery only if there's one to show...
        if len(parsed_galleries) == 1:
            gallery = parsed_galleries[0]
            await self.imageboard.show_preview(msg, gallery.url, board=gallery.group, guide=gallery.guide, only_if_missing=only_if_missing)

        elif len(parsed_galleries) > 1:
            common_domain = parsed_galleries[0].group
            for parsed_gallery in parsed_galleries:
                if parsed_gallery.group != common_domain:
                    common_domain = ""
                    print("Skipping previews. The links sent do not belong to the same domain.")
                    break

            if common_domain:
                guide = parsed_galleries[0].guide
                gallery_urls: list[str] = [e.url for e in parsed_galleries]
                await self.imageboard.show_combined_preview(msg, gallery_urls, board=common_domain, guide=guide, only_if_missing=only_if_missing)

    def command_was_issued(self, msg: discord.Message) -> bool:
        if (command_name_regex := COMMAND_PATTERN.search(msg.content)):
            cmd: commands.Command = self.bot.get_command(command_name_regex.group(1))
            return bool(cmd)
        return False

    async def check_quiet_channels(self, msg: discord.Message, botstatus_cog: BotStatus, valid_interaction: bool) -> None:
        channel_id: str = str(msg.channel.id)

        if self.bot.last_channel != channel_id or msg.attachments or valid_interaction:
            self.bot.last_channel = channel_id
            self.bot.last_channel_message_count = 0
            return

        self.bot.last_channel_message_count += 1

        if channel_id not in self.bot.rules['quiet_channels']:
            return

        max_messages_without_embeds = self.bot.rules['quiet_channels'][channel_id]['max_messages_without_embeds']

        if not self.bot.last_channel_warned and self.bot.last_channel_message_count >= max_messages_without_embeds:
            self.bot.last_channel_warned = True
            quote_line = botstatus_cog.get_quote('quiet_channel_past_threshold')
            await botstatus_cog.typing_a_message(msg.channel, content=quote_line, rnd_duration=[1, 2])

    @commands.Cog.listener()
    async def on_ready(self):
        """On bot start"""
        print(f'Logged in to Discord  [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')

        # Change play status to something fitting
        await self.bot.change_presence(activity=discord.Game(name=self.botstatus.get_quote('playing_status')))

    @commands.Cog.listener()
    async def on_connect(self):
        """On connect"""
        print(f'Connected to server [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')

        if self.bot.connect_time:
            delta_time = datetime.utcnow() - self.bot.connect_time
            (hours, remainder) = divmod(int(delta_time.total_seconds()), 3600)
            (minutes, seconds) = divmod(remainder, 60)
            (days, hours) = divmod(hours, 24)
            print(f'Downtime for {days} days, {hours:02d}:{minutes:02d}:{seconds:02d}')

        self.bot.isconnected = True
        self.bot.connect_time = datetime.utcnow()

    @commands.Cog.listener()
    async def on_disconnect(self):
        """On disconnect"""
        if self.bot.isconnected:
            print(f'Disconnected from server [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')
            self.bot.isconnected = False


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(BotEvents(bot))
