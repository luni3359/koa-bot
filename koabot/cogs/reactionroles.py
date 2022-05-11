"""All about reaction roles"""
import json
import re
import timeit
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import discord
import emoji
from dataclass_wizard import JSONSerializable
from dataclass_wizard.enums import LetterCase
from discord.ext import commands

from koabot.cogs.botstatus import BotStatus
from koabot.kbot import KBot
from koabot.patterns import CHANNEL_URL_PATTERN, DISCORD_EMOJI_PATTERN


@dataclass
class RRLink():
    reactions: set
    roles: list[int]


@dataclass()
class RRBind():
    message_id: int
    channel_id: int
    links: list[RRLink] = field(default_factory=list)


@dataclass
class RRSavedBind(JSONSerializable):
    class _(JSONSerializable.Meta):
        key_transform_with_dump = LetterCase.SNAKE

    channel_id: int
    links: list[RRLink]


@dataclass
class RRConfirmation():
    bind_tag: str
    reactions: Any
    link: RRLink


@dataclass
class RRWatch():
    channel_id: int
    links: list[RRLink]


@dataclass
class RRCooldown():
    cooldown_start: float
    change_count: int


def is_guild_owner():
    """Demo custom check that checks whether or the caller is the owner"""
    def predicate(ctx: commands.Context):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)


class ReactionRoles(commands.Cog):
    """ReactionRoles class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.rr_unsaved_binds = {}
        self.rr_confirmations = {}
        self.rr_assignments = {}
        self.rr_cooldown = {}
        self.spam_limit = 12

        self.migrate_json_to_db()
        self.load_rr_binds()

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    def load_rr_binds(self):
        binds_file = Path(self.bot.DATA_DIR, "binds.json")

        if not binds_file.exists():
            binds_file.touch()
            return

        with open(binds_file, 'r', encoding="UTF-8") as json_file:
            data = json.load(json_file)

            for k, v in data.items():
                message_id: int = int(k)
                channel_id: int = int(v['channel_id'])
                links: list[RRLink] = v['links']
                self.add_rr_watch(message_id, channel_id, links)

    def migrate_json_to_db(self):
        """Placeholder for a future port method"""

    async def assign_roles(self, reaction: str, user: discord.Member, message_id: int, channel_id: int):
        """Updates the roles of the given user
        Parameters:
            reaction::str
            user::discord.Member
            message_id::int
            channel_id::int
        """
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        message_reactions: set[str] = set()

        for em in message.reactions:
            if not isinstance(em, str):
                em = str(em)

            message_reactions.add(em)

        rr_watch: RRWatch = self.rr_assignments[message_id]

        bound_reactions = set()
        for link in rr_watch.links:
            bound_reactions.update(link.reactions)

        reactions_in_use = bound_reactions.intersection(message_reactions)
        reactions_by_currentuser = []

        for rct in message.reactions:
            if not isinstance(rct.emoji, str):
                em = str(rct.emoji)
            else:
                em = rct.emoji

            if em not in reactions_in_use:
                continue

            async for u in rct.users():
                if u.id != user.id:
                    continue

                reactions_by_currentuser.append(em)

        # match with links
        for link in rr_watch.links:
            if not isinstance(link.reactions, set):
                link.reactions = set(link.reactions)

            link_fully_matches = link.reactions.issubset(reactions_by_currentuser)

            if reaction not in link.reactions:
                continue

            role_removal = False
            if not link_fully_matches:
                reactions_by_currentuser.append(reaction)
                role_removal = link.reactions.issubset(reactions_by_currentuser)

                if not role_removal:
                    continue

            roles: list[discord.Role] = list(map(channel.guild.get_role, link.roles))

            if len(link.roles) > 1:
                role_string = ', '.join(f"**@{r.name}**" for r in roles)
            else:
                role_string = f"**@{roles[0].name}**"

            singular_or_plural_roles = "roles" if len(roles) > 1 else "role"

            try:
                if role_removal:
                    quote = f"{user.mention}, say goodbye to {role_string}..."
                    await user.remove_roles(*roles, reason="Requested by the own user by reacting")
                else:
                    quote = f"Congrats, {user.mention}. You get the {role_string} {singular_or_plural_roles}!"
                    await user.add_roles(*roles, reason="Requested by the own user by reacting")
            except discord.Forbidden:
                print(f"Missing permissions to grant \"{user.name}\" roles on \"{channel.guild.name}\"")

            try:
                print(quote)
                await user.send(quote)
            except discord.Forbidden:
                print(f"I couldn't notify {user.name} about {role_string}...")

    @commands.group(aliases=['reactionroles', 'reactionrole', 'rr'])
    @commands.check_any(commands.is_owner(), is_guild_owner())
    async def reaction_roles(self, ctx: commands.Context):
        """Grant users roles upon reacting to a message"""
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command!')

    @reaction_roles.command()
    async def assign(self, ctx: commands.Context, url: str = "") -> None:
        """Initialize the reaction roles binding process"""
        if not (url_matches := CHANNEL_URL_PATTERN.match(url)):
            return await ctx.send(self.botstatus.get_quote('rr_assign_missing_or_invalid_message_url'))

        url_components = url_matches.group(0).split('/')
        message_id: int = int(url_components[-1])
        channel_id: int = int(url_components[-2])
        server_id: int = int(url_components[-3])

        if channel_id != ctx.channel.id:
            target_channel = self.bot.get_channel(channel_id)
        else:
            target_channel = ctx.channel

        message: discord.Message = None
        try:
            message = await target_channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send(self.botstatus.get_quote('rr_assign_message_url_not_found'))
        except discord.Forbidden:
            await ctx.send("I don't have permissions to interact with that message...")
        except discord.HTTPException:
            await ctx.send("Network issues. Please try again in a few moments.")

        if not message:
            return

        # make a queue for the emojis for the current user if it doesn't exist
        author_id = ctx.author.id

        if (bind_tag := f"{author_id}/{server_id}") in self.rr_unsaved_binds:
            return await ctx.send(self.botstatus.get_quote('rr_assign_already_assigning'))

        self.rr_unsaved_binds[bind_tag] = RRBind(message_id, channel_id)

        await ctx.send(self.botstatus.get_quote('rr_assign_process_complete'))

    @reaction_roles.command()
    async def bind(self, ctx: commands.Context) -> None:
        """Add a new emoji-role binding to the message being currently assigned to"""
        if (bind_tag := f"{ctx.message.author.id}/{ctx.guild.id}") not in self.rr_unsaved_binds:
            return await ctx.send(self.botstatus.get_quote('rr_message_target_missing'))

        reacted_emojis = set(re.findall(DISCORD_EMOJI_PATTERN, ctx.message.content) +
                             re.findall(emoji.get_emoji_regexp(), ctx.message.content))
        mentioned_roles = ctx.message.role_mentions

        exit_reason = None
        if not reacted_emojis and not mentioned_roles:
            exit_reason = "one emoji and one role"
        elif not reacted_emojis:
            exit_reason = "one emoji"
        elif not mentioned_roles:
            exit_reason = "one role"

        if exit_reason:
            kusudama, party_popper = [emoji.emojize(em) for em in [":confetti_ball:", ":tada:"]]
            return await ctx.send(f"Please include at least {exit_reason} to bind to. How you arrange them does not matter.\n\nFor example:\n{kusudama} @Party → Reacting with {kusudama} will assign the @Party role.\n{party_popper} @Party @Yay {kusudama} → Reacting with {kusudama} AND {party_popper} will assign the @Party and @Yay roles.")

        bind: RRBind = self.rr_unsaved_binds[bind_tag]

        # prevent duplicate role bindings from being created
        link_to_overwrite = None
        for link in bind.links:
            if len(mentioned_roles) != len(link.roles):
                continue

            roles_are_duplicate = True
            for rl in mentioned_roles:
                if rl.id not in link.roles:
                    roles_are_duplicate = False
                    break

            if roles_are_duplicate:
                # check if the emojis are also identical
                if len(reacted_emojis) != len(link.reactions):
                    link_to_overwrite = link
                    break

                for em in reacted_emojis:
                    if em not in link.reactions:
                        link_to_overwrite = link
                        break

                # if reactions are also identical
                if not link_to_overwrite:
                    await ctx.message.add_reaction(emoji.emojize(":interrobang:", use_aliases=True))
                    await ctx.send("You've already made this binding before!")
                    return

                break

        if link_to_overwrite:
            em_joined = " AND ".join(reacted_emojis)
            rl_joined = " AND ".join([ctx.guild.get_role(v).mention for v in link_to_overwrite.roles])
            maru, batu = [emoji.emojize(em, use_aliases=True) for em in [":o:", ":x:"]]
            tmp_msg: discord.Message = await ctx.send(f"This binding already exists. Would you like to change it to the following?\n\nReact to {em_joined} to get {rl_joined}\n\nSelect {maru} to overwrite, or {batu} to ignore this binding.")

            self.add_rr_confirmation(tmp_msg.id, bind_tag, link_to_overwrite, reacted_emojis)

            for em in [maru, batu]:
                await tmp_msg.add_reaction(em)
            return

        bind.links.append(RRLink(reacted_emojis, [rl.id for rl in mentioned_roles]))
        await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    @reaction_roles.command()
    async def undo(self, ctx: commands.Context, call_type: str) -> None:
        """Cancel the last issued reaction roles entry"""
        if (bind_tag := f"{ctx.message.author.id}/{ctx.guild.id}") not in self.rr_unsaved_binds:
            await ctx.send(self.botstatus.get_quote('rr_message_target_missing'))
            return

        bind: RRBind = self.rr_unsaved_binds[bind_tag]

        match call_type:
            case 'last':
                bind.links.pop()
            case 'all':
                bind.links = []

    @reaction_roles.command()
    async def save(self, ctx: commands.Context) -> None:
        """Complete the emoji-role registration"""
        if (bind_tag := f"{ctx.message.author.id}/{ctx.guild.id}") not in self.rr_unsaved_binds:
            return await ctx.send(self.botstatus.get_quote('rr_message_target_missing'))

        bind: RRBind = self.rr_unsaved_binds[bind_tag]

        if not bind.links:
            return await ctx.send(self.botstatus.get_quote('rr_save_cannot_save_empty'))

        print("Saving bind...")

        self.add_rr_watch(bind.message_id, bind.channel_id, bind.links)

        target_message: discord.Message = await self.bot.get_channel(bind.channel_id).fetch_message(bind.message_id)

        for link in bind.links:
            # can't map async
            # map(await message.add_reaction, link['reactions'])
            for reaction in link.reactions:
                await target_message.add_reaction(reaction)

        # TODO: Possible optimization: don't open the file twice if possible
        # create file if it doesn't exist
        binds_file = Path(self.bot.DATA_DIR, "binds.json")

        if not binds_file.exists():
            with open(binds_file, 'w', encoding="UTF-8") as json_file:
                json_file.write("{}")

        with open(binds_file, 'r+', encoding="UTF-8") as json_file:
            saved_bind = RRSavedBind(bind.channel_id, bind.links)

            j_data = json.load(json_file)
            j_data[bind.message_id] = saved_bind.to_dict()
            print(j_data)

            json_file.seek(0)
            json_file.write(json.dumps(j_data, indent=4))
            json_file.truncate()

        self.rr_unsaved_binds.pop(bind_tag)
        await ctx.send("Registration complete!")

    @reaction_roles.command(aliases=['quit', 'exit', 'stop'])
    async def cancel(self, ctx: commands.Context) -> None:
        """Quit the reaction roles binding process"""
        if (bind_tag := f"{ctx.message.author.id}/{ctx.guild.id}") not in self.rr_unsaved_binds:
            await ctx.send(self.botstatus.get_quote('rr_message_target_missing'))
        else:
            self.rr_unsaved_binds.pop(bind_tag)
            await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    async def reaction_added(self, payload: discord.RawReactionActionEvent, user: discord.Member | discord.User):
        """When a reaction is added to a message"""
        # Handle reaction role
        if payload.message_id in self.rr_assignments:
            if await self.manage_rr_cooldown(user):
                return

            await self.assign_roles(str(payload.emoji), user, payload.message_id, payload.channel_id)
        # Handle confirmation
        elif payload.message_id in self.rr_confirmations:
            confirmation: RRConfirmation = self.rr_confirmations[payload.message_id]

            if payload.user_id != confirmation.bind_tag.split('/')[0]:
                return

            valid_options = [emoji.emojize(em, use_aliases=True) for em in [":o:", ":x:"]]

            if (reaction := str(payload.emoji)) not in valid_options:
                return

            if reaction == emoji.emojize(':o:', use_aliases=True):
                confirmation.link.reactions = confirmation.reactions

            self.rr_confirmations.pop(payload.message_id)

            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.clear_reactions()

            if reaction == emoji.emojize(':o:', use_aliases=True):
                outcome_emoji = ":white_check_mark:"
            else:
                outcome_emoji = ":stop_sign:"

            await message.add_reaction(emoji.emojize(outcome_emoji, use_aliases=True))

    async def reaction_removed(self, payload: discord.RawReactionActionEvent, user: discord.Member | discord.User):
        """When a reaction is removed from a message"""
        # Handle reaction role
        if payload.message_id in self.rr_assignments:
            if await self.manage_rr_cooldown(user):
                return

            await self.assign_roles(str(payload.emoji), user, payload.message_id, payload.channel_id)

    async def manage_rr_cooldown(self, user: discord.User) -> bool:
        """Prevents users from overloading role requests"""
        current_time = timeit.default_timer()

        if user.id not in self.rr_cooldown:
            self.rr_cooldown[user.id] = RRCooldown(current_time, 0)

        user_cooldown: RRCooldown = self.rr_cooldown[user.id]
        time_diff = current_time - user_cooldown.cooldown_start

        # if too many reactions were sent
        if user_cooldown.change_count > self.spam_limit:
            if time_diff < 60:
                return True

            user_cooldown.cooldown_start = current_time
            user_cooldown.change_count = 0

        # refresh cooldown if two minutes have passed
        if time_diff > 120:
            user_cooldown.cooldown_start = current_time
            user_cooldown.change_count = 0
        elif time_diff < 1:
            user_cooldown.change_count += 3
        elif time_diff < 5:
            user_cooldown.change_count += 2
        else:
            user_cooldown.change_count += 1

        # send a warning and freeze if spammed
        if user_cooldown.change_count > self.spam_limit:
            user_cooldown.cooldown_start = current_time
            await user.send("Please wait a few moments and try again.")
            return True

        return False

    def add_rr_confirmation(self, message_id: int, bind_tag: str, single_link: list, reactions: list) -> None:
        """Creates an entry pending to be handled for reaction roles overwrite request"""
        rr_confirmation = RRConfirmation(bind_tag, reactions, single_link)
        self.rr_confirmations[message_id] = rr_confirmation

    def add_rr_watch(self, message_id: int, channel_id: int, links: list[RRLink]) -> None:
        """Starts keeping track of what messages have bound actions"""
        rr_watch = RRWatch(channel_id, links)
        self.rr_assignments[message_id] = rr_watch


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(ReactionRoles(bot))
