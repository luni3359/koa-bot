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
from koabot.patterns import URL_PATTERN


class BotEvents(commands.Cog):
    """BotEvents class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.connect_time = None
        self.bot.isconnected = False
        self.bot.last_channel = 0
        self.bot.last_channel_message_count = 0
        self.bot.last_channel_warned = False

        # guides stuff
        self.valid_urls = []
        for group, contents in self.bot.match_groups.items():
            for match in contents:
                url_pattern = match['url']
                url_pattern = url_pattern.replace(r'.', r'\.')
                url_pattern = url_pattern.replace(r'*', r'(.*?)')
                self.valid_urls.append({'group': group, 'url': url_pattern, 'guide': match['guide']})

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

        rr_cog: ReactionRoles = self.bot.get_cog("ReactionRoles")
        await rr_cog.reaction_added(payload, user)

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

        rr_cog: ReactionRoles = self.bot.get_cog("ReactionRoles")
        await rr_cog.reaction_removed(payload, user)

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

        # TODO: Walrus opportunity
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

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

        author: discord.abc.User = msg.author
        content: str = msg.content

        # Prevent bot from spamming itself
        if author.bot:
            return

        if msg.guild is None:
            print(f'{author.name}#{author.discriminator} ({author.id}): {content}')
            return

        # Beta bot overrides me in the servers we share
        beta_bot_id = self.bot.koa['discord_user']['beta_id']

        # if it's a normal user
        if author.id not in self.bot.testing['debug_users']:
            # ...and i'm the debug instance
            if msg.guild.me.id == beta_bot_id:
                # do nothing
                return
        # if it's a debug user
        else:
            beta_bot: discord.Member = msg.guild.get_member(beta_bot_id)

            # ...and the debug instance is online
            if beta_bot and beta_bot.status == discord.Status.online:
                # ...and i'm not the debug instance
                if msg.guild.me.id != beta_bot_id:
                    # do nothing
                    return

        channel: discord.TextChannel = msg.channel

        # Reference channels together
        if len(content) and content[0] == '!' and msg.channel_mentions:  # only if explicitly asked for
            bot_cog: BotStatus = self.bot.get_cog('BotStatus')

            for mentioned_channel in msg.channel_mentions:
                if mentioned_channel == channel:
                    continue

                embed_template = discord.Embed()
                embed_template.set_author(name=author.display_name, icon_url=author.avatar_url)
                embed_template.set_footer(text=msg.guild.name, icon_url=msg.guild.icon_url)

                target_embed = embed_template.copy()
                target_embed.description = bot_cog.get_quote(
                    'channel_linking_target', author=author.mention, channel=channel.mention, msg_url=msg.jump_url)
                target_channel_msg = await mentioned_channel.send(embed=target_embed)

                origin_embed = embed_template.copy()
                origin_embed.description = bot_cog.get_quote(
                    'channel_linking_origin', author=author.mention, channel=mentioned_channel.mention, msg_url=target_channel_msg.jump_url)
                await channel.send(embed=origin_embed)

        url_matches_found = []
        escaped_url = False
        i = 0
        while i < len(content):
            # check for urls, ignoring those with escaped embeds
            if content[i] == '<':
                escaped_url = True
                i += 1
                continue

            url_match = URL_PATTERN.match(content, i)
            # TODO Soon... in Python 3.8
            # if (url_match := URL_PATTERN.match(content, i)):
            if url_match:
                if not escaped_url or url_match.end() >= len(content) or url_match.end() < len(content) and content[url_match.end()] != '>':
                    url_matches_found.append(
                        {'full_url': url_match.group(),
                         'fqdn': tldextract.extract(url_match.group()).fqdn})

                i = url_match.end()
                continue

            escaped_url = False
            i += 1

        gallery = []
        for url_match in url_matches_found:
            for valid_url in self.valid_urls:
                group = valid_url['group']
                url_pattern = valid_url['url']
                guides = valid_url['guide']

                # match() matches only from the start of the string
                if not re.match(url_pattern, url_match['fqdn']):
                    continue

                for guide in guides:
                    guide_type = guide['type']
                    guide_name = guide['name']

                    try:
                        guide_content = self.bot.guides[guide_type][guide_name]
                    except KeyError as e:
                        print(f'KeyError: "{e.args[0]}" is an undefined guide name or type .')
                        continue

                    full_url = url_match['full_url']

                    if guide_type == 'gallery':
                        gallery.append({'url': full_url, 'board': group, 'guide': guide_content})
                    elif guide_type == 'stream' and group == 'picarto':
                        streams_cog: StreamService = self.bot.get_cog('StreamService')
                        picarto_preview_shown = await streams_cog.get_picarto_stream_preview(msg, full_url)

                        if picarto_preview_shown and content[0] == '!':
                            await msg.delete()

                # done with this url
                break

        # post gallery only if there's one to show...
        if len(gallery) == 1:
            imageboard_cog: ImageBoard = self.bot.get_cog('ImageBoard')

            gallery = gallery[0]
            gallery_board = gallery['board']
            requested_by_user = content[0] != '!'

            # ...only if it was asked for by starting their message with '!', for booru galleries
            if gallery_board in ['danbooru', 'e621', 'sankaku']:
                await imageboard_cog.show_gallery(msg, gallery['url'], board=gallery_board, guide=gallery['guide'], only_missing_preview=requested_by_user)
            # or if it's anything else
            else:
                await imageboard_cog.show_gallery(msg, gallery['url'], board=gallery_board, guide=gallery['guide'])

        # checking if a command has been issued
        command_issued = False
        if len(content) and content[0] == '!':
            command_name_regex = re.search(r'^!([a-zA-Z0-9]+)', content)
            if command_name_regex:
                cmd = self.bot.get_command(command_name_regex.group(1))
                command_issued = bool(cmd)

        if self.bot.last_channel != channel.id or url_matches_found or msg.attachments or command_issued:
            self.bot.last_channel = channel.id
            self.bot.last_channel_message_count = 0
        else:
            self.bot.last_channel_message_count += 1

        if str(channel.id) in self.bot.rules['quiet_channels']:
            if not self.bot.last_channel_warned and self.bot.last_channel_message_count >= self.bot.rules['quiet_channels'][str(channel.id)]['max_messages_without_embeds']:
                self.bot.last_channel_warned = True
                bot_cog: BotStatus = self.bot.get_cog('BotStatus')

                await bot_cog.typing_a_message(channel, content=bot_cog.get_quote('quiet_channel_past_threshold'), rnd_duration=[1, 2])

    @commands.Cog.listener()
    async def on_ready(self):
        """On bot start"""
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')
        print(f'Logged in to Discord  [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')

        # Change play status to something fitting
        await self.bot.change_presence(activity=discord.Game(name=bot_cog.get_quote('playing_status')))

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


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(BotEvents(bot))
