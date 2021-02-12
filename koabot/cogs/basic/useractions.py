"""Get user information"""
import re

import discord
import emoji
from discord.ext import commands
from koabot.patterns import CHANNEL_URL_PATTERN, DISCORD_EMOJI_PATTERN


class UserActions(commands.Cog):
    """UserActions class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rr_temporary_list = {}

    @commands.command(aliases=['ava'])
    async def avatar(self, ctx):
        """Display the avatar of an user"""

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

    @commands.group(aliases=['rr'])
    async def reaction_roles(self, ctx):
        """Grant users roles upon reacting to a message"""
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command!')

    @reaction_roles.command()
    async def assign(self, ctx, url: str):
        url_matches = CHANNEL_URL_PATTERN.match(url)

        if not url_matches:
            await ctx.send('Please send a valid message link to bind to. Right-click the message you want to use, and click "Copy Message Link". It should look something like this: \n`https://discord.com/channels/123456789123456789/123456789123456789/123456789123456789`')
            return

        message_id = int(url_matches.group(0).split('/')[-1])
        message = None

        channel_id = int(url_matches.group(0).split('/')[-2])
        if channel_id != ctx.channel.id:
            target_channel = self.bot.get_channel(channel_id)
        else:
            target_channel = ctx.channel

        try:
            message = await target_channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send('Hmm... That message link is correct, but it doesn\'t seem to work. Did you get the wrong url, or was it removed?')
        except discord.Forbidden:
            await ctx.send('I don\'t have permissions to interact with that message...')
        except discord.HTTPException:
            await ctx.send('Network issues. Please try again in a few moments.')

        if not message:
            return

        # make a queue for the emojis for the current user if it doesn't exist
        author_id = ctx.author.id
        server_id = url_matches.group(0).split('/')[-3]
        bind_tag = f'{author_id}/{server_id}'
        if bind_tag in self.rr_temporary_list:
            await ctx.send('You\'re already in the process of assigning roles and emojis to this message!')
            return

        self.rr_temporary_list[bind_tag] = {}
        self.rr_temporary_list[bind_tag]['bind_message'] = message_id
        self.rr_temporary_list[bind_tag]['rr_links'] = []

        await ctx.send('I will listen to your messages now. Ping your roles (preferably in a hidden channel) along with any number of emojis and they will seamlessly bind each other when they\'re reacted to. As long as your messages contain only emojis and roles, I will accept them.\n\nIf you\'re not satisfied with a change you made, please use `!rr undo last` to undo the latest input I accepted, or `!rr undo all` to start from scratch.\n\nOnce you\'re done, please run the command `!rr save`. If you don\'t want to proceed, call `!rr cancel` to quit.')

    @reaction_roles.command()
    async def bind(self, ctx):
        """Add a new binding to the current message in use"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            await ctx.send('You\'re not currently assigning any bindings!')

        emoji_list = set(re.findall(DISCORD_EMOJI_PATTERN, ctx.message.content) + re.findall(emoji.get_emoji_regexp(), ctx.message.content))
        roles_list = [rl.id for rl in ctx.message.role_mentions]

        exit_reason = None
        if not emoji_list and not roles_list:
            exit_reason = 'one emoji and one role'
        elif not emoji_list:
            exit_reason = 'one emoji'
        elif not roles_list:
            exit_reason = 'one role'

        if exit_reason:
            exit_emoji = emoji.emojize(':confetti_ball:')
            exit_emoji2 = emoji.emojize(':tada:')
            await ctx.send(f'Please include at least {exit_reason} to bind to. How you arrange them does not matter.\n\nFor example:\n{exit_emoji} \@Party → Reacting with {exit_emoji} will assign the \@Party role.\n{exit_emoji2} \@Party \@Yay {exit_emoji} → Reacting with {exit_emoji} AND {exit_emoji2} will assign the \@Party and \@Yay roles.')
            return

        # prevent duplicate role bindings from being created
        binding_to_overwrite = None
        for binding in self.rr_temporary_list[bind_tag]['rr_links']:
            if len(roles_list) != len(binding['roles']):
                continue

            roles_are_duplicate = True
            for rl in roles_list:
                if rl not in binding['roles']:
                    roles_are_duplicate = False

            if roles_are_duplicate:
                # check if the emojis are also identical
                if len(emoji_list) != len(binding['reactions']):
                    binding_to_overwrite = binding
                    break

                for em in emoji_list:
                    if em not in binding['reactions']:
                        binding_to_overwrite = binding
                        break

                # reactions are also identical
                if not binding_to_overwrite:
                    await ctx.message.add_reaction(emoji.emojize(':interrobang:', use_aliases=True))
                    await ctx.send('You\'ve already made this binding before!')
                    return

                break

        if binding_to_overwrite:
            em_joined = ' AND '.join(emoji_list)
            rl_joined = ' AND '.join([str(rl) for rl in binding_to_overwrite['roles']])
            maru = emoji.emojize(':o:', use_aliases=True)
            batu = emoji.emojize(':x:', use_aliases=True)
            tmp_msg = await ctx.send(f'This binding already exists. Would you like to change it to the following?\n\nReact to {em_joined} to get {rl_joined}\n\nSelect {maru} to overwrite, or {batu} to ignore this binding.')
            await tmp_msg.add_reaction(maru)
            await tmp_msg.add_reaction(batu)
            return

        # if binding_to_overwrite:
        #     bind_object = binding_to_overwrite
        #     bind_object['reactions'] = set(bind_object['reactions'] + emoji_list)
        # else:
        bind_object = {}
        bind_object['reactions'] = emoji_list
        bind_object['roles'] = roles_list

        self.rr_temporary_list[bind_tag]['rr_links'].append(bind_object)

        await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

    @reaction_roles.command()
    async def undo(self, ctx):
        """Cancel the last issued reaction roles entry"""
        pass

    @reaction_roles.command()
    async def save(self, ctx):
        """Complete the role-emoji registration"""
        pass

    @reaction_roles.command(aliases=['quit', 'exit', 'stop'])
    async def cancel(self, ctx):
        """Quit the reaction roles binding process"""
        bind_tag = f'{ctx.message.author.id}/{ctx.guild.id}'

        if bind_tag not in self.rr_temporary_list:
            await ctx.send('You\'re not currently assigning any bindings!')
        else:
            self.rr_temporary_list.pop(bind_tag)
            await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))



def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
