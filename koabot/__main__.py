"""Koakuma bot"""
import asyncio
import os
import sqlite3
import timeit
from contextlib import closing
from datetime import datetime
from pathlib import Path
from sys import argv

import appdirs
import commentjson
import discord

from koabot.kbot import BaseDirectory, KBot

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent
PROJECT_NAME = PROJECT_DIR.name

DATA_DIR = Path(appdirs.user_data_dir(PROJECT_NAME))
CONFIG_DIR = Path(appdirs.user_config_dir(PROJECT_NAME))
CACHE_DIR = Path(appdirs.user_cache_dir(PROJECT_NAME))


def set_base_directories(bot: KBot):
    # Create base directories if they're missing
    for base_dir in [DATA_DIR, CONFIG_DIR, CACHE_DIR]:
        base_dir.mkdir(exist_ok=True)

    bot.set_base_directory(BaseDirectory.PROJECT_NAME, PROJECT_NAME)
    bot.set_base_directory(BaseDirectory.PROJECT_DIR, PROJECT_DIR)
    bot.set_base_directory(BaseDirectory.MODULE_DIR, MODULE_DIR)
    bot.set_base_directory(BaseDirectory.DATA_DIR, DATA_DIR)
    bot.set_base_directory(BaseDirectory.CONFIG_DIR, CONFIG_DIR)
    bot.set_base_directory(BaseDirectory.CACHE_DIR, CACHE_DIR)


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
        db_file = Path(CACHE_DIR, "dbBeta.sqlite3")
    else:
        data_filenames.insert(0, "config.jsonc")
        db_file = Path(CACHE_DIR, "db.sqlite3")

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
        # Generate tables in database
        schema = "db/database.sql"
        with open(schema, encoding="UTF-8") as file:
            sql_script = file.read()

        bot.sqlite_conn = sqlite3.connect(db_file)

        with closing(bot.sqlite_conn.cursor()) as cursor:
            cursor.executescript(sql_script)
            bot.sqlite_conn.commit()

        print(f"To database in {timeit.default_timer() - start_load_time:0.3f}s")
    except PermissionError:
        print(f"Unable to open file {schema}")
    except FileNotFoundError:
        print(f"Couldn't find {schema}")
    except sqlite3.Error as e:
        print(e.with_traceback)
        print("Could not connect to the database! Functionality will be limited.")

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
