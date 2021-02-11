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
        author_id = str(ctx.author.id)
        if author_id not in self.rr_temporary_list:
            self.rr_temporary_list[author_id] = {}

        bind_tag = f'{channel_id}/{message_id}'
        if bind_tag in self.rr_temporary_list[author_id]:
            await ctx.send('You\'re already in the process of assigning roles and emojis to this message!')
            return

        self.rr_temporary_list[author_id][bind_tag] = []

        await ctx.send('I will listen to your messages now. Ping your roles (preferably in a hidden channel) along with any number of emojis and they will seamlessly bind each other when they\'re reacted to. As long as your messages contain only emojis and roles, I will accept them.\n\nIf you\'re not satisfied with a change you made, please use `!rr undo last` to undo the latest input I accepted, or `!rr undo all` to start from scratch.\n\nOnce you\'re done, please run the command `!rr save`. If you don\'t want to proceed, call `!rr cancel` to quit.')

    @reaction_roles.command()
    async def bind(self, ctx):
        """Add a new binding to the current message in use"""
        x = ''
        for role in ctx.message.role_mentions:
            x += role.name + ', '

        e = ''
        emoji_list = set(re.findall(DISCORD_EMOJI_PATTERN, ctx.message.content) + re.findall(emoji.get_emoji_regexp(), ctx.message.content))

        for em in emoji_list:
            e += em + ', '

        test = await ctx.send(f'Roles sent: {x}\nEmojis sent: {e}')

        # for em in emoji_list:
            # await test.add_reaction(em)

        await ctx.message.add_reaction(emoji.emojize(':white_check_mark:', use_aliases=True))

        # self.rr_temporary_list[author_id][bind_tag].append()

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
        pass


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(UserActions(bot))
