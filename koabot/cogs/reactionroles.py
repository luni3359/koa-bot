"""All about reaction roles"""
import json
import os
import re
import timeit

import discord
import emoji
from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.kbot import KBot
from koabot.patterns import CHANNEL_URL_PATTERN, DISCORD_EMOJI_PATTERN


def is_guild_owner():
    """Demo custom check that checks whether or the caller is the owner"""
    def predicate(ctx: commands.Context):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)


class ReactionRoles(commands.Cog):
    """ReactionRoles class"""

    def __init__(self, bot: KBot):
        self.bot = bot
        self.rr_temporary_list = {}
        self.rr_confirmations = {}
        self.rr_assignments = {}
        self.rr_cooldown = {}
        self.spam_limit = 12

        # load reaction role binds
        file_path = os.path.join(self.bot.DATA_DIR, 'binds.json')
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding="UTF-8") as json_file:
                j_data = json.load(json_file)

                for message_id, v in j_data.items():
                    self.add_rr_watch(message_id, v['channel_id'], v['links'])

    async def assign_roles(self, emoji_sent: str, user: discord.Member, message_id: int, channel_id: int):
        """Updates the roles of the given user
        Parameters:
            user::discord.Member
            message_id::int
            channel_id::int
        """
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        user_id = user.id

        message_reactions: set[str] = set()
        for em in message.reactions:
            if not isinstance(em, str):
                em = str(em)

            message_reactions.add(em)

        bound_reactions = set()
        for link in self.rr_assignments[str(message_id)]['links']:
            bound_reactions.update(link['reactions'])

        reactions_in_use = bound_reactions.intersection(message_reactions)
        reactions_by_currentuser = []

        for reaction in message.reactions:
            if not isinstance(reaction.emoji, str):
                em = str(reaction.emoji)
            else:
                em = reaction.emoji

            if em not in reactions_in_use:
                continue

            for u in await reaction.users().flatten():
                if u.id != user_id:
                    continue

                reactions_by_currentuser.append(em)

        # match with links
        for link in self.rr_assignments[str(message_id)]['links']:
            if not isinstance(link['reactions'], set):
                link['reactions'] = set(link['reactions'])

            link_fully_matches = link['reactions'].issubset(reactions_by_currentuser)

            if emoji_sent not in link['reactions']:
                continue

            role_removal = False
            if not link_fully_matches:
                reactions_by_currentuser.append(emoji_sent)
                role_removal = link['reactions'].issubset(reactions_by_currentuser)

                if not role_removal:
                    continue

            if not isinstance(link['roles'][0], discord.Role):
                link['roles'] = list(map(channel.guild.get_role, link['roles']))

            if role_removal:
                await user.remove_roles(*link['roles'], reason='Requested by the own user by reacting')
                quote = f'{user.mention}, say goodbye to XX...'
            else:
                await user.add_roles(*link['roles'], reason='Requested by the own user by reacting')
                quote = f'Congrats, {user.mention}. You get the XX YY!'

            if len(link['roles']) > 1:
                roles = ', '.join(f"**@{r.name}**" for r in link['roles'])
            else:
                roles = link['roles'][0].name
                roles = f"**@{roles}**"

            quote = quote.replace('XX', roles)
            quote = quote.replace('YY', 'roles' if len(link['roles']) > 1 else 'role')

            try:
                print(quote)
                await user.send(quote)
            except discord.Forbidden:
                print(f"I couldn't notify {user.name} about {roles}...")

    @commands.group(aliases=['reactionroles', 'reactionrole', 'rr'])
    @commands.check_any(commands.is_owner(), is_guild_owner())
    async def reaction_roles(self, ctx: commands.Context):
        """Grant users roles upon reacting to a message"""
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command!')

    @reaction_roles.command()
    async def assign(self, ctx: commands.Context, url: str) -> None:
        """Initialize the emoji-message-role binding process"""
        url_matches = CHANNEL_URL_PATTERN.match(url)
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')
        if not url_matches:
            return await ctx.send(bot_cog.get_quote('rr_assign_missing_or_invalid_message_url'))

        message_id = url_matches.group(0).split('/')[-1]
        message: discord.Message = None

        channel_id = url_matches.group(0).split('/')[-2]
        if channel_id != ctx.channel.id:
            target_channel = self.bot.get_channel(int(channel_id))
        else:
            target_channel = ctx.channel

        try:
            message = await target_channel.fetch_message(int(message_id))
        except discord.NotFound:
            await ctx.send(bot_cog.get_quote('rr_assign_message_url_not_found'))
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
            return await ctx.send(bot_cog.get_quote('rr_assign_already_assigning'))

        tmp_bind = {}
        tmp_bind['bind_message'] = message_id
        tmp_bind['bind_channel'] = channel_id
        tmp_bind['links'] = []
        self.rr_temporary_list[bind_tag] = tmp_bind

        await ctx.send(bot_cog.get_quote('rr_assign_process_complete'))

    @reaction_roles.command()
    async def bind(self, ctx: commands.Context) -> None:
        """Add a new emoji-role binding to the message being currently assigned to"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        if bind_tag not in self.rr_temporary_list:
            return await ctx.send(bot_cog.get_quote('rr_message_target_missing'))

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

            self.add_rr_confirmation(tmp_msg.id, bind_tag, link_to_overwrite, emoji_list)

            await tmp_msg.add_reaction(maru)
            await tmp_msg.add_reaction(batu)
            return

        bind_object = {}
        bind_object['reactions'] = emoji_list
        bind_object['roles'] = roles_list
        self.rr_temporary_list[bind_tag]['links'].append(bind_object)

        await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    @reaction_roles.command()
    async def undo(self, ctx: commands.Context, call_type: str) -> None:
        """Cancel the last issued reaction roles entry"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        if bind_tag not in self.rr_temporary_list:
            await ctx.send(bot_cog.get_quote('rr_message_target_missing'))
            return

        match call_type:
            case 'last':
                self.rr_temporary_list[bind_tag]['links'].pop()
            case 'all':
                self.rr_temporary_list[bind_tag]['links'] = []

    @reaction_roles.command()
    async def save(self, ctx: commands.Context) -> None:
        """Complete the emoji-role registration"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        if bind_tag not in self.rr_temporary_list:
            return await ctx.send(bot_cog.get_quote('rr_message_target_missing'))

        tmp_root: dict = self.rr_temporary_list[bind_tag]

        if not tmp_root['links']:
            return await ctx.send(bot_cog.get_quote('rr_save_cannot_save_empty'))

        print('Saving bind...')
        bind_channel = tmp_root['bind_channel']
        bind_message = tmp_root['bind_message']
        links = tmp_root['links']

        file_name = 'binds.json'
        file_path = os.path.join(self.bot.DATA_DIR, file_name)

        self.add_rr_watch(bind_message, bind_channel, links)

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
    async def cancel(self, ctx: commands.Context) -> None:
        """Quit the reaction roles binding process"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'
        bot_cog: BotStatus = self.bot.get_cog('BotStatus')

        if bind_tag not in self.rr_temporary_list:
            await ctx.send(bot_cog.get_quote('rr_message_target_missing'))
        else:
            self.rr_temporary_list.pop(bind_tag)
            await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    async def reaction_added(self, payload: discord.RawReactionActionEvent, user: discord.abc.User):
        """When a reaction is added to a message"""
        # Handle reaction role
        if str(payload.message_id) in self.rr_assignments:
            if await self.manage_rr_cooldown(user):
                return

            await self.assign_roles(str(payload.emoji), user, payload.message_id, payload.channel_id)
        # Handle confirmation
        elif str(payload.message_id) in self.rr_confirmations:
            tmp_root = self.rr_confirmations[payload.message_id]

            if str(payload.user_id) != tmp_root['bind_tag'].split('/')[0]:
                return

            reaction = payload.emoji

            valid_options = [emoji.emojize(':o:', use_aliases=True), emoji.emojize(':x:', use_aliases=True)]

            if str(reaction) not in valid_options:
                return

            if str(reaction) == emoji.emojize(':o:', use_aliases=True):
                self.rr_conflict_response(tmp_root['link'], tmp_root['emoji_list'])
            else:
                self.rr_conflict_response(None, None)

            self.rr_confirmations.pop(payload.message_id)

            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.clear_reactions()

            if str(reaction) == emoji.emojize(':o:', use_aliases=True):
                await message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))
            else:
                await message.add_reaction(emoji.emojize(':stop_sign:', use_aliases=True))

    async def reaction_removed(self, payload: discord.RawReactionActionEvent, user: discord.abc.User):
        """When a reaction is removed from a message"""
        # Handle reaction role
        if str(payload.message_id) in self.rr_assignments:
            if await self.manage_rr_cooldown(user):
                return

            await self.assign_roles(str(payload.emoji), user, payload.message_id, payload.channel_id)

    @staticmethod
    def rr_conflict_response(rr_link, emoji_list):
        """Complete or drop the request to assign chosen emoji to a reactionrole link"""
        if not emoji_list:
            return

        rr_link['reactions'] = emoji_list

    async def manage_rr_cooldown(self, user: discord.User) -> bool:
        """Prevents users from overloading role requests"""
        current_time = timeit.default_timer()
        user_id = str(user.id)

        if user_id not in self.rr_cooldown:
            tmp_obj = {}
            tmp_obj['cooldown_start'] = current_time
            tmp_obj['change_count'] = 0
            self.rr_cooldown[user_id] = tmp_obj

        tmp_root = self.rr_cooldown[user_id]
        time_diff = current_time - tmp_root['cooldown_start']

        # if too many reactions were sent
        if tmp_root['change_count'] > self.spam_limit:
            if time_diff < 60:
                return True

            tmp_root['cooldown_start'] = current_time
            tmp_root['change_count'] = 0

        # refresh cooldown if two minutes have passed
        if time_diff > 120:
            tmp_root['cooldown_start'] = current_time
            tmp_root['change_count'] = 0
        elif time_diff < 1:
            tmp_root['change_count'] += 3
        elif time_diff < 5:
            tmp_root['change_count'] += 2
        else:
            tmp_root['change_count'] += 1

        # send a warning and freeze
        if tmp_root['change_count'] > self.spam_limit:
            tmp_root['cooldown_start'] = current_time
            await user.send("Please wait a few moments and try again.")
            return True

        return False

    def add_rr_confirmation(self, message_id: str, bind_tag: str, single_link: list, emoji_list: list) -> None:
        """Creates an entry pending to be handled for reaction roles overwrite request"""
        self.rr_confirmations[message_id] = {}
        self.rr_confirmations[message_id]['bind_tag'] = bind_tag
        self.rr_confirmations[message_id]['emoji_list'] = emoji_list
        self.rr_confirmations[message_id]['link'] = single_link

    def add_rr_watch(self, message_id: str, channel_id: str, links: list) -> None:
        """Starts keeping track of what messages have bound actions"""
        tmp_obj = {}
        tmp_obj['channel_id'] = channel_id
        tmp_obj['links'] = links

        self.rr_assignments[message_id] = tmp_obj


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(ReactionRoles(bot))
