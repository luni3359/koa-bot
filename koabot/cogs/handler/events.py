"""Bot events"""
import random
import re
from datetime import datetime

import discord
import tldextract
from discord.ext import commands
from koabot.patterns import URL_PATTERN
from mergedeep import merge


class BotEvents(commands.Cog):
    """BotEvents class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.connect_time = None
        self.bot.isconnected = False
        self.bot.last_channel = 0
        self.bot.last_channel_message_count = 0
        self.bot.last_channel_warned = False

        self.valid_urls = []
        for group, contents in self.bot.match_groups.items():
            for match in contents:
                url_pattern = match['url']
                url_pattern = url_pattern.replace('.', '\.')
                url_pattern = url_pattern.replace('*', '(.*?)')
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

                source_guide.update(merge(target_guide, source_guide))

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

        # Prevent bot from spamming itself
        if msg.author.bot:
            return

        # Beta bot overrides me in the servers we share
        beta_bot_id = self.bot.koa['discord_user']['beta_id']

        # if it's a normal user
        if msg.author.id not in self.bot.testing['debug_users']:
            # ...and i'm the debug instance
            if msg.guild.me.id == beta_bot_id:
                # do nothing
                return
        # if it's a debug user
        else:
            beta_bot = msg.guild.get_member(beta_bot_id)

            # ...and the debug instance is online
            if beta_bot and beta_bot.status == discord.Status.online:
                # ...and i'm not the debug instance
                if msg.guild.me.id != beta_bot_id:
                    # do nothing
                    return

        channel = msg.channel

        # Reference channels together
        for mentioned_channel in msg.channel_mentions:
            if mentioned_channel == channel:
                continue

            embed_template = discord.Embed()
            embed_template.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
            embed_template.set_footer(text=msg.guild.name, icon_url=msg.guild.icon_url)

            target_embed = embed_template.copy()
            target_embed.description = f'Mention by {msg.author.mention} from {channel.mention}\n\n[Click to go there]({msg.jump_url})'
            target_channel_msg = await mentioned_channel.send(embed=target_embed)

            origin_embed = embed_template.copy()
            origin_embed.description = f'Mention by {msg.author.mention} to {mentioned_channel.mention}\n\n[Click to go there]({target_channel_msg.jump_url})'
            await channel.send(embed=origin_embed)

        url_matches_found = []
        escaped_url = False
        i = 0
        while i < len(msg.content):
            # check for urls, ignoring those with escaped embeds
            if msg.content[i] == '<':
                escaped_url = True
                i += 1
                continue

            url_match = URL_PATTERN.match(msg.content, i)
            # TODO Soon... in Python 3.8
            # if (url_match := URL_PATTERN.match(msg.content, i)):
            if url_match:
                if not escaped_url or url_match.end() >= len(msg.content) or url_match.end() < len(msg.content) and msg.content[url_match.end()] != '>':
                    url_matches_found.append({'full_url': url_match.group(), 'fqdn': tldextract.extract(url_match.group()).fqdn})

                i = url_match.end()
                continue

            escaped_url = False
            i += 1

        expended_groups = []
        for url_match in url_matches_found:
            for valid_url in self.valid_urls:
                group = valid_url['group']
                url_pattern = valid_url['url']
                guides = valid_url['guide']

                # ignore rules from repeated groups
                if group in expended_groups:
                    continue

                # match() matches only from the start of the string
                if not re.match(url_pattern, url_match['fqdn']):
                    continue

                for guide in guides:
                    guide_type = guide['type']
                    guide_name = guide['name']

                    if not self.bot.guides[guide_type][guide_name]:
                        raise ValueError('Undefined guide.')

                    full_url = url_match['full_url']
                    expended_groups.append(group)

                    if guide_type == 'gallery':
                        imageboard_cog = self.bot.get_cog('ImageBoard')
                        await imageboard_cog.show_gallery(msg, full_url, board=group, guide=self.bot.guides[guide_type][guide_name])
                    elif guide_type == 'stream' and group == 'picarto':
                        streams_cog = self.bot.get_cog('StreamService')
                        picarto_preview_shown = await streams_cog.get_picarto_stream_preview(msg, full_url)

                        if picarto_preview_shown and msg.content[0] == '!':
                            await msg.delete()

                # done with this url
                break

        if self.bot.last_channel != channel.id or url_matches_found or msg.attachments:
            self.bot.last_channel = channel.id
            self.bot.last_channel_message_count = 0
        else:
            self.bot.last_channel_message_count += 1

        if str(channel.id) in self.bot.rules['quiet_channels']:
            if not self.bot.last_channel_warned and self.bot.last_channel_message_count >= self.bot.rules['quiet_channels'][str(channel.id)]['max_messages_without_embeds']:
                self.bot.last_channel_warned = True
                bot_cog = self.bot.get_cog('BotStatus')

                await bot_cog.typing_a_message(channel, content=random.choice(self.bot.quotes['quiet_channel_past_threshold']), rnd_duration=[1, 2])

    @commands.Cog.listener()
    async def on_ready(self):
        """On bot start"""

        print(f'Logged in to Discord  [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')

        # Change play status to something fitting
        await self.bot.change_presence(activity=discord.Game(name=random.choice(self.bot.quotes['playing_status'])))

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
