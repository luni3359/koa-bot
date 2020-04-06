"""Bot events"""
import asyncio
import random

import discord
from discord.ext import commands

from koabot.patterns import URL_PATTERN


class BotEvents(commands.Cog):
    """BotEvents class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_channel = 0
        self.last_channel_message_count = 0
        self.last_channel_warned = False

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

        beta_bot = msg.guild.get_member(self.bot.koa['discord_user']['beta_id'])
        if beta_bot and beta_bot.status == discord.Status.online and msg.guild.me.id != self.bot.koa['discord_user']['beta_id']:
            # Beta bot overrides me in the servers we share
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
            target_embed.description = 'Mention by {} from {}\n\n[Click to go there]({})'.format(msg.author.mention, channel.mention, msg.jump_url)
            target_channel_msg = await mentioned_channel.send(embed=target_embed)

            origin_embed = embed_template.copy()
            origin_embed.description = 'Mention by {} to {}\n\n[Click to go there]({})'.format(msg.author.mention, mentioned_channel.mention, target_channel_msg.jump_url)
            await channel.send(embed=origin_embed)

        url_matches = []
        escaped_url = False
        i = 0
        while i < len(msg.content):
            if msg.content[i] == '<':
                escaped_url = True
                i += 1
                continue

            url_match = URL_PATTERN.match(msg.content, i)
            if url_match:
                if not escaped_url or url_match.end() >= len(msg.content) or url_match.end() < len(msg.content) and msg.content[url_match.end()] != '>':
                    url_matches.append(url_match.group())

                i = url_match.end()
                continue

            escaped_url = False
            i += 1

        for url in url_matches:
            for domain_name, asset in self.bot.assets.items():
                if 'domain' in self.bot.assets[domain_name] and asset['domain'] in url and 'type' in asset:
                    if asset['type'] == 'gallery':
                        if domain_name == 'deviantart':
                            await globals()['get_{}_post'.format(domain_name)](msg, url)
                        else:
                            await globals()['get_{}_gallery'.format(domain_name)](msg, url)
                    elif asset['type'] == 'stream' and domain_name == 'picarto':
                        picarto_preview_shown = await get_picarto_stream_preview(msg, url)
                        if picarto_preview_shown and msg.content[0] == '!':
                            await msg.delete()

        if self.last_channel != channel.id or url_matches or msg.attachments:
            self.last_channel = channel.id
            self.last_channel_message_count = 0
        else:
            self.last_channel_message_count += 1

        if str(channel.id) in self.bot.rules['quiet_channels']:
            if not self.last_channel_warned and self.last_channel_message_count >= self.bot.rules['quiet_channels'][str(channel.id)]['max_messages_without_embeds']:
                self.last_channel_warned = True
                await koa_is_typing_a_message(channel, content=random.choice(self.bot.quotes['quiet_channel_past_threshold']), rnd_duration=[1, 2])

    @commands.Cog.listener()
    async def on_ready(self):
        """On bot start"""

        print('Ready!')
        # Change play status to something fitting
        await self.bot.change_presence(activity=discord.Game(name=random.choice(self.bot.quotes['playing_status'])))


async def koa_is_typing_a_message(ctx, **kwargs):
    """Make Koakuma seem alive with a 'is typing' delay

    Keywords:
        content::str
            Message to be said.
        embed::discord.Embed
            Self-explanatory. Default is None.
        rnd_duration::list or int
            A list with two int values of what's the least that should be waited for to the most, chosen at random.
            If provided an int the 0 will be assumed at the start.
        min_duration::int
            The amount of time that will be waited regardless of rnd_duration.
    """

    content = kwargs.get('content')
    embed = kwargs.get('embed')
    rnd_duration = kwargs.get('rnd_duration')
    min_duration = kwargs.get('min_duration', 0)

    if isinstance(rnd_duration, int):
        rnd_duration = [0, rnd_duration]

    async with ctx.typing():
        if rnd_duration:
            time_to_wait = random.randint(rnd_duration[0], rnd_duration[1])
            if time_to_wait < min_duration:
                time_to_wait = min_duration
            await asyncio.sleep(time_to_wait)
        else:
            await asyncio.sleep(min_duration)

        if embed is not None:
            if content:
                await ctx.send(content, embed=embed)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(content)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(BotEvents(bot))
