"""Koakuma bot"""
import asyncio
import os
import sqlite3
import timeit
from datetime import datetime
from pathlib import Path
from sys import argv

import appdirs
import commentjson
import discord
from discord.ext import commands

from koabot.kbot import BaseDirectory, KBot

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent
PROJECT_NAME = PROJECT_DIR.name

DATA_DIR = Path(appdirs.user_data_dir(PROJECT_NAME))
CONFIG_DIR = Path(appdirs.user_config_dir(PROJECT_NAME))
CACHE_DIR = Path(appdirs.user_cache_dir(PROJECT_NAME))

# Create base directories if they're missing
for base_dir in [DATA_DIR, CONFIG_DIR, CACHE_DIR]:
    base_dir.mkdir(exist_ok=True)


def set_base_directories(bot: KBot):
    bot.set_base_directory(BaseDirectory.PROJECT_NAME, PROJECT_NAME)
    bot.set_base_directory(BaseDirectory.PROJECT_DIR, PROJECT_DIR)
    bot.set_base_directory(BaseDirectory.MODULE_DIR, MODULE_DIR)
    bot.set_base_directory(BaseDirectory.DATA_DIR, DATA_DIR)
    bot.set_base_directory(BaseDirectory.CONFIG_DIR, CONFIG_DIR)
    bot.set_base_directory(BaseDirectory.CACHE_DIR, CACHE_DIR)


async def debug_check(ctx: commands.Context) -> bool:
    """Disable live instance for specific users if a beta instance is running"""

    # ignore everything in DMs
    if ctx.guild is None:
        return False

    # if the author is not a debug user
    if ctx.author.id not in bot.testing['debug_users']:
        return not bot.debug_mode

    if not bot.debug_mode:
        beta_bot_id = bot.koa['discord_user']['beta_id']
        beta_bot: discord.Member = ctx.guild.get_member(beta_bot_id)

        # if the beta bot is online
        if beta_bot and beta_bot.status == discord.Status.online:
            return False

    return True


async def main():
    print(f"Starting {PROJECT_NAME}...")
    bot.launch_time = datetime.utcnow()
    bot.debug_mode = '--debug' in argv
    set_base_directories(bot)

    bot_data = {}
    data_filenames = [
        "auth.jsonc",
        "quotes.jsonc"
    ]

    if bot.debug_mode:
        print('Running in debug mode.')
        data_filenames.insert(0, "beta.jsonc")
    else:
        data_filenames.insert(0, "config.jsonc")

    for filename in data_filenames:
        try:
            config_file = Path(CONFIG_DIR, filename)
            with open(config_file, encoding="UTF-8") as json_file:
                bot_data.update(commentjson.load(json_file))
        except FileNotFoundError as e:
            print(e)

    bot.__dict__.update(bot_data)

    print("Connecting to database...")
    start_load_time = timeit.default_timer()

    try:
        db_file = Path(CACHE_DIR, "dbBeta.sqlite3")
        bot.sqlite_conn = sqlite3.connect(db_file)

        # Generate tables in database
        with open("db/database.sql", encoding="UTF-8") as f:
            sql_script = f.read()

        c = bot.sqlite_conn.cursor()
        c.executescript(sql_script)
        bot.sqlite_conn.commit()
        c.close()
        print(f"To database in {timeit.default_timer() - start_load_time:0.3f}s")
    except sqlite3.Error as e:
        print(e)
        print("Could not connect to the database! Functionality will be limited.")

    bot.add_check(debug_check)

    async with bot:
        await bot.load_all_extensions()
        await bot.start(bot.koa['token'])

bot = KBot(command_prefix='!', description='', intents=discord.Intents.all())

if __name__ == '__main__':
    # Installs async optimizations for compatible systems
    if os.name == "posix":
        try:
            import uvloop
            uvloop.install()
        except ModuleNotFoundError as e:
            print(f"{e.name} is not installed.")

    asyncio.run(main())
