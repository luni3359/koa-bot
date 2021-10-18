"""Get user information"""
import json
import os
import random
import re

import discord
import emoji
from discord.ext import commands

from koabot.cogs.handler.events import BotEvents
from koabot.koakuma import DATA_DIR
from koabot.patterns import CHANNEL_URL_PATTERN, DISCORD_EMOJI_PATTERN


def is_guild_owner():
    """Demo custom check that checks whether or the caller is the owner"""
    def predicate(ctx: commands.Context):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rr_temporary_list = {}

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx: commands.Context):
        """Display an user's avatar"""

        if ctx.message.mentions:
            for mention in ctx.message.mentions:
                embed = discord.Embed()
                embed.set_image(url=mention.avatar_url)
                embed.set_author(
                    name=f'{mention.name} #{mention.discriminator}',
                    icon_url=mention.avatar_url)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed()
            embed.set_image(url=ctx.message.author.avatar_url)
            embed.set_author(
                name=f'{ctx.message.author.name} #{ctx.message.author.discriminator}',
                icon_url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.group(aliases=['reactionroles', 'reactionrole', 'rr'])
    @commands.check_any(commands.is_owner(), is_guild_owner())
    async def reaction_roles(self, ctx: commands.Context):
        """Grant users roles upon reacting to a message"""
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command!')

    @reaction_roles.command()
    async def assign(self, ctx: commands.Context, url: str):
        """Initialize the emoji-message-role binding process"""
        url_matches = CHANNEL_URL_PATTERN.match(url)

        if not url_matches:
            await ctx.send(random.choice(self.bot.quotes['rr_assign_missing_or_invalid_message_url']))
            return

        message_id = url_matches.group(0).split('/')[-1]
        message = None

        channel_id = url_matches.group(0).split('/')[-2]
        if channel_id != ctx.channel.id:
            target_channel = self.bot.get_channel(int(channel_id))
        else:
            target_channel = ctx.channel

        try:
            message = await target_channel.fetch_message(int(message_id))
        except discord.NotFound:
            await ctx.send(random.choice(self.bot.quotes['rr_assign_message_url_not_found']))
        except discord.Forbidden:
            await ctx.send("I don't have permissions to interact with that message...")
        except discord.HTTPException:
            await ctx.send('Network issues. Please try again in a few moments.')

        if not message:
            return

        # make a queue for the emojis for the current user if it doesn't exist
        author_id = ctx.author.id
        server_id = url_matches.group(0).split('/')[-3]
        bind_tag = f'{author_id}/{server_id}'
        if bind_tag in self.rr_temporary_list:
            return await ctx.send(random.choice(self.bot.quotes['rr_assign_already_assigning']))

        self.rr_temporary_list[bind_tag] = {}
        self.rr_temporary_list[bind_tag]['bind_message'] = message_id
        self.rr_temporary_list[bind_tag]['bind_channel'] = channel_id
        self.rr_temporary_list[bind_tag]['links'] = []

        await ctx.send(random.choice(self.bot.quotes['rr_assign_process_complete']))

    @reaction_roles.command()
    async def bind(self, ctx: commands.Context):
        """Add a new emoji-role binding to the message being currently assigned to"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            return await ctx.send(random.choice(self.bot.quotes['rr_message_target_missing']))

        emoji_list = set(re.findall(DISCORD_EMOJI_PATTERN, ctx.message.content) +
                         re.findall(emoji.get_emoji_regexp(), ctx.message.content))
        roles_list = ctx.message.role_mentions

        exit_reason = None
        if not emoji_list and not roles_list:
            exit_reason = 'one emoji and one role'
        elif not emoji_list:
            exit_reason = 'one emoji'
        elif not roles_list:
            exit_reason = 'one role'

        if exit_reason:
            kusudama = emoji.emojize(':confetti_ball:')
            party_popper = emoji.emojize(':tada:')
            return await ctx.send(f'Please include at least {exit_reason} to bind to. How you arrange them does not matter.\n\nFor example:\n{kusudama} @Party → Reacting with {kusudama} will assign the @Party role.\n{party_popper} @Party @Yay {kusudama} → Reacting with {kusudama} AND {party_popper} will assign the @Party and @Yay roles.')

        # prevent duplicate role bindings from being created
        link_to_overwrite = None
        for link in self.rr_temporary_list[bind_tag]['links']:
            if len(roles_list) != len(link['roles']):
                continue

            roles_are_duplicate = True
            for rl in roles_list:
                if rl not in link['roles']:
                    roles_are_duplicate = False

            if roles_are_duplicate:
                # check if the emojis are also identical
                if len(emoji_list) != len(link['reactions']):
                    link_to_overwrite = link
                    break

                for em in emoji_list:
                    if em not in link['reactions']:
                        link_to_overwrite = link
                        break

                # reactions are also identical
                if not link_to_overwrite:
                    await ctx.message.add_reaction(emoji.emojize(':interrobang:', use_aliases=True))
                    await ctx.send("You've already made this binding before!")
                    return

                break

        if link_to_overwrite:
            em_joined = ' AND '.join(emoji_list)
            rl_joined = ' AND '.join([rl.mention for rl in link_to_overwrite['roles']])
            maru = emoji.emojize(':o:', use_aliases=True)
            batu = emoji.emojize(':x:', use_aliases=True)
            tmp_msg: discord.Message = await ctx.send(f'This binding already exists. Would you like to change it to the following?\n\nReact to {em_joined} to get {rl_joined}\n\nSelect {maru} to overwrite, or {batu} to ignore this binding.')

            events_cog: BotEvents = self.bot.get_cog('BotEvents')
            events_cog.add_rr_confirmation(tmp_msg.id, bind_tag, link_to_overwrite, emoji_list)

            await tmp_msg.add_reaction(maru)
            await tmp_msg.add_reaction(batu)
            return

        bind_object = {}
        bind_object['reactions'] = emoji_list
        bind_object['roles'] = roles_list

        self.rr_temporary_list[bind_tag]['links'].append(bind_object)

        await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    @reaction_roles.command()
    async def undo(self, ctx: commands.Context, call_type: str):
        """Cancel the last issued reaction roles entry"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            await ctx.send(random.choice(self.bot.quotes['rr_message_target_missing']))
            return

        if call_type == 'last':
            self.rr_temporary_list[bind_tag]['links'].pop()
        elif call_type == 'all':
            self.rr_temporary_list[bind_tag]['links'] = []

    @reaction_roles.command()
    async def save(self, ctx: commands.Context):
        """Complete the emoji-role registration"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            return await ctx.send(random.choice(self.bot.quotes['rr_message_target_missing']))

        tmp_root: dict = self.rr_temporary_list[bind_tag]

        if not tmp_root['links']:
            return await ctx.send(random.choice(self.bot.quotes['rr_save_cannot_save_empty']))

        print('Saving bind...')
        bind_channel = tmp_root['bind_channel']
        bind_message = tmp_root['bind_message']
        links = tmp_root['links']

        file_name = 'binds.json'
        file_path = os.path.join(DATA_DIR, file_name)

        events_cog: BotEvents = self.bot.get_cog('BotEvents')
        events_cog.add_rr_watch(bind_message, bind_channel, links)

        target_message: discord.Message = await self.bot.get_channel(int(bind_channel)).fetch_message(int(bind_message))

        for link in links:
            # can't map async
            # map(await message.add_reaction, link['reactions'])

            for reaction in link['reactions']:
                await target_message.add_reaction(reaction)

        # TODO: Possible optimization: don't open the file twice if possible
        # create file if it doesn't exist
        if not os.path.isfile(file_path):
            with open(file_path, 'w', encoding="UTF-8") as json_file:
                json_file.write('{}')

        with open(file_path, 'r+', encoding="UTF-8") as json_file:
            tmp_obj = {}
            tmp_obj['channel_id'] = bind_channel
            tmp_obj['links'] = links

            j_data = json.load(json_file)
            j_data[bind_message] = tmp_obj

            for link in j_data[bind_message]['links']:
                link['reactions'] = list(link['reactions'])
                link['roles'] = [r.id for r in link['roles']]

            json_file.seek(0)
            json_file.write(json.dumps(j_data))
            json_file.truncate()

        self.rr_temporary_list.pop(bind_tag)

        await ctx.send('Registration complete!')

    @reaction_roles.command(aliases=['quit', 'exit', 'stop'])
    async def cancel(self, ctx: commands.Context):
        """Quit the reaction roles binding process"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            await ctx.send(random.choice(self.bot.quotes['rr_message_target_missing']))
        else:
            self.rr_temporary_list.pop(bind_tag)
            await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    @staticmethod
    def rr_conflict_response(rr_link, emoji_list):
        """Complete or drop the request to assign chosen emoji to a reactionrole link"""
        if not emoji_list:
            return

        rr_link['reactions'] = emoji_list
        
    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def _reload(self, ctx: commands.Context, *, module: str):
        """Reloads a module"""
        if module == "all":
            pass

        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f"{type(e).__name__}: {e}")
        else:
            await ctx.send(f"Successfully reloaded '{module}'.")

def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
