import os
import sys
import traceback

import commentjson
import discord
from discord.ext import commands

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(PROJECT_DIR, 'config.jsonc')) as json_file:
    data = commentjson.load(json_file)


def get_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    prefixes = ['!']

    # Check to see if we are outside of a guild. e.g DM's etc.
    if not message.guild:
        # Only allow ! to be used in DMs
        return '!'

    # If we are in a guild, we allow for the user to mention us or use any of the prefixes in our list.
    return commands.when_mentioned_or(*prefixes)(bot, message)


# Below cogs represents our folder our cogs are in. Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = [
    # 'cogs.members',
    # 'cogs.owner',
    # 'cogs.simple'
    'cogs.linkparser',
    'cogs.twitter'
]

bot = commands.Bot(command_prefix=get_prefix, description='A Rewrite Cog Example')
bot.__dict__.update(data)

# Here we load our extensions(cogs) listed above in [initial_extensions].
if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print('Failed to load extension %s.' % extension, file=sys.stderr)
            traceback.print_exc()


@bot.event
async def on_ready():
    """http://discordpy.readthedocs.io/en/rewrite/api.html#discord.on_ready"""

    print('\n\nLogged in as: %s - %s\nVersion: %s\n' % (bot.user.name, bot.user.id, discord.__version__))

    await bot.change_presence(activity=discord.Game(name='with books'))
    print(f'Successfully logged in and booted...!')


bot.run(bot.auth_keys['discord']['token'], bot=True, reconnect=True)
