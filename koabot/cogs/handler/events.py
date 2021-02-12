"""Bot events"""
import random
import re
from datetime import datetime

import discord
import emoji
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
        self.rr_confirmations = {}
        self.rr_assignments = {}

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

                combined_guide = merge({}, target_guide, source_guide)
                self.bot.guides[guide_type][guide_name] = combined_guide

    def add_rr_confirmation(self, message_id, bind_tag, emoji_list):
        self.rr_confirmations[message_id] = {}
        self.rr_confirmations[message_id]['bind_tag'] = bind_tag
        self.rr_confirmations[message_id]['emoji_list'] = emoji_list

    def add_rr_watch(self, message_id, links):
        self.rr_assignments[message_id] = links

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        handle_confirmation = payload.message_id in self.rr_confirmations
        handle_reactionrole = payload.message_id in self.rr_assignments

        if handle_confirmation:
            tmp_root = self.rr_confirmations[payload.message_id]

            if str(payload.user_id) != tmp_root['bind_tag'].split('/')[0]:
                return

            reaction = payload.emoji

            valid_options = [emoji.emojize(':o:', use_aliases=True), emoji.emojize(':x:', use_aliases=True)]

            if reaction.name not in valid_options:
                pass

            useractions_cog = self.bot.get_cog('UserActions')
            useractions_cog.rr_conflict_response(tmp_root['bind_tag'], tmp_root['emoji_list'])

            self.rr_confirmations.pop(payload.message_id)

            channel = self.bot.get_channel(payload.channel_id)

            message = await channel.fetch_message(payload.message_id)
            await message.clear_reactions()
            await message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))
        elif handle_reactionrole:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            emojis_in_message = [str(em) for em in message.reactions if not isinstance(em, str)]
            emojis_in_message += [em for em in message.reactions if isinstance(em, str)]
            emojis_in_message = set(emojis_in_message)

            emojis_in_links = set()

            for link in self.rr_assignments[payload.message_id]:
                # get only reactions with bound emojis
                emojis_in_links.update(link['reactions'])

            emojis_in_use = emojis_in_links.intersection(emojis_in_message)
            users_that_reacted = {}

            for reaction in message.reactions:
                if not isinstance(reaction.emoji, str):
                    em = str(reaction.emoji)
                else:
                    em = reaction.emoji

                if em not in emojis_in_use:
                    continue

                for user in await reaction.users().flatten():
                    if user.id not in users_that_reacted:
                        users_that_reacted[user.id] = {}
                        users_that_reacted[user.id]['discord_user'] = user
                        users_that_reacted[user.id]['reactions'] = []

                    users_that_reacted[user.id]['reactions'].append(em)

            # match with links
            for link in self.rr_assignments[payload.message_id]:
                for user_id, user_contents in users_that_reacted.items():
                    link_fully_matches = link['reactions'].issubset(user_contents['reactions'])

                    if not link_fully_matches:
                        continue

                    user_mention = user_contents['discord_user'].mention

                    if len(link['roles']) > 1:
                        roles = ', '.join(str(r) for r in link['roles'])
                        await channel.send(f'Congrats, {user_mention}. You get the {roles} roles!')
                    else:
                        role = link['roles'][0]
                        await channel.send(f'Congrats, {user_mention}. You get the {role} role!')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        channel = self.bot.get_channel(payload.channel_id)
        member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
        print(f'{member.mention} removed an emoji!')

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
                        streams_cog = self.bot.get_cog('StreamService')
                        picarto_preview_shown = await streams_cog.get_picarto_stream_preview(msg, full_url)

                        if picarto_preview_shown and msg.content[0] == '!':
                            await msg.delete()

                # done with this url
                break

        # post gallery only if there's one to show
        if len(gallery) == 1:
            gallery = gallery[0]
            imageboard_cog = self.bot.get_cog('ImageBoard')
            await imageboard_cog.show_gallery(msg, gallery['url'], board=gallery['board'], guide=gallery['guide'])

        # checking if a command has been issued
        command_issued = False
        if msg.content[0] == '!':
            command_name_regex = re.search(r'^!([a-zA-Z0-9]+)', msg.content)
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
