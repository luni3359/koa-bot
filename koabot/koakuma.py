"""Koakuma bot"""
import os
import sqlite3
import timeit
import traceback
from datetime import datetime
from pathlib import Path

import appdirs
import commentjson
import discord
from discord.ext import commands

import koabot.tasks

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = Path(SOURCE_DIR).parent
BOT_DIRNAME = 'koa-bot'

DATA_DIR = appdirs.user_data_dir(BOT_DIRNAME)
CONFIG_DIR = appdirs.user_config_dir(BOT_DIRNAME)
CACHE_DIR = appdirs.user_cache_dir(BOT_DIRNAME)

# Create base directories if they're absent
for b_dir in [DATA_DIR, CONFIG_DIR, CACHE_DIR]:
    os.makedirs(b_dir, exist_ok=True)

# Install uvloop in compatible systems
if os.name == "posix":
    try:
        import uvloop
        uvloop.install()
    except ModuleNotFoundError as e:
        print(f"{e.name} is not installed.")

intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', description='', intents=intents)


def run_periodic_tasks() -> None:
    """Bot routines"""
    bot.loop.create_task(koabot.tasks.check_live_streamers())
    bot.loop.create_task(koabot.tasks.change_presence_periodically())


def load_all_extensions(path: str) -> None:
    """Recursively load all cogs in the project"""
    print('Loading cogs in project...')

    start_load_time = timeit.default_timer()
    cog_prefix = 'koabot.cogs'
    cog_list = []
    dropped_cogs = 0

    for p, _, f in os.walk(path):
        for file in f:
            if file.endswith('.py'):
                container_dir = p.replace(path, '').replace('/', '.')
                (filename, _) = os.path.splitext(file)

                if filename == "__init__":
                    continue

                cog_path = cog_prefix + container_dir + '.' + filename
                cog_list.append(cog_path)

    for ext in cog_list:
        try:
            print(f"Loading \"{ext}\"...".ljust(40), end='\r')
            bot.load_extension(ext)
        except commands.errors.ExtensionFailed as e:
            dropped_cogs += 1
            print(e)
            print(f"Failed to load \"{ext}\".")

    time_to_finish = timeit.default_timer() - start_load_time

    if dropped_cogs == 0:
        log_msg = f"Finished loading {len(cog_list)} cogs in {time_to_finish:0.2f}s."
    else:
        log_msg = f"WARNING: Only {len(cog_list)-dropped_cogs}/{len(cog_list)} succesfully loaded (in {time_to_finish:0.2f}s)."

    print(log_msg.ljust(40))


@bot.check
async def debug_check(ctx: commands.Context) -> bool:
    """Disable live instance for specific users if a beta instance is running"""

    # ignore everything in DMs
    if ctx.guild is None:
        return False

    # if the author is not a debug user
    if ctx.author.id not in bot.testing['debug_users']:
        return not bot.is_beta

    if not bot.is_beta:
        beta_bot_id = bot.koa['discord_user']['beta_id']
        beta_bot: discord.Member = ctx.guild.get_member(beta_bot_id)

        # if the beta bot is online
        if beta_bot and beta_bot.status == discord.Status.online:
            return False

    return True


def start(debugging: bool = False, /):
    """Starts the bot"""
    print(f"Starting {BOT_DIRNAME}...")
    bot.launch_time = datetime.utcnow()
    bot.is_beta = debugging
    bot_data = {}

    data_filenames = [
        'auth.jsonc',
        'quotes.jsonc'
    ]

    if debugging:
        print('Running in debug mode.')
        data_filenames.insert(0, 'beta.jsonc')
    else:
        data_filenames.insert(0, 'config.jsonc')

    for filename in data_filenames:
        try:
            with open(os.path.join(CONFIG_DIR, filename), encoding="UTF-8") as json_file:
                bot_data.update(commentjson.load(json_file))
        except FileNotFoundError as e:
            print(e)

    bot.__dict__.update(bot_data)

    print('Connecting to database...')
    start_load_time = timeit.default_timer()

    try:
        bot.sqlite_conn = sqlite3.connect(os.path.join(CACHE_DIR, 'dbBeta.sqlite3'))

        # Generate tables in database
        with open('db/database.sql', encoding="UTF-8") as f:
            sql_script = f.read()

        c = bot.sqlite_conn.cursor()
        c.executescript(sql_script)
        bot.sqlite_conn.commit()
        c.close()
        print(f'To database in {timeit.default_timer() - start_load_time:0.3f}s')
    except sqlite3.Error as e:
        print(e)
        print('Could not connect to the database! Functionality will be limited.')

    load_all_extensions(os.path.join(SOURCE_DIR, 'cogs'))
    run_periodic_tasks()

    bot.run(bot.koa['token'])
