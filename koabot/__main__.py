"""Koakuma bot"""
import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from sys import argv

import aiosqlite
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


def set_base_directories(bot: KBot) -> None:
    # Create base directories if they're missing
    for base_dir in [DATA_DIR, CONFIG_DIR, CACHE_DIR]:
        base_dir.mkdir(parents=True, exist_ok=True)

    bot.set_base_directory(BaseDirectory.PROJECT_NAME, PROJECT_NAME)
    bot.set_base_directory(BaseDirectory.PROJECT_DIR, PROJECT_DIR)
    bot.set_base_directory(BaseDirectory.MODULE_DIR, MODULE_DIR)
    bot.set_base_directory(BaseDirectory.DATA_DIR, DATA_DIR)
    bot.set_base_directory(BaseDirectory.CONFIG_DIR, CONFIG_DIR)
    bot.set_base_directory(BaseDirectory.CACHE_DIR, CACHE_DIR)


async def create_database_schema(conn: aiosqlite.Connection) -> None:
    """Generate tables in database"""
    schema = "db/database.sql"
    with open(schema, encoding="UTF-8") as file:
        sql_script = file.read()

    async with conn.cursor() as cursor:
        await cursor.executescript(sql_script)
        await conn.commit()


def db_migration_setup(db_name: str) -> None:
    """Fixes the location of the database to DATA_DIR"""
    source = Path(CACHE_DIR, db_name)
    destination = Path(DATA_DIR, db_name)

    if source.is_file():
        if destination.is_file():
            return print("ERROR: Unable to move database. A database already exists at destination."
                         f"\nSource: {source}\nDestination:{destination}\n")

        print(f"The database has been moved from \"{CACHE_DIR}\" to \"{destination}\"")
        shutil.move(source, destination)


async def main():
    print(f"Starting {PROJECT_NAME}...")
    bot.launch_time = datetime.utcnow()
    bot.debug_mode = ('--debug' in argv) or os.environ.get("KOABOT_DEBUG", False)
    set_base_directories(bot)

    bot_data = {}
    data_filenames = [
        "auth.jsonc",
        "quotes.jsonc"
    ]

    if bot.debug_mode:
        print("Running in debug mode.")
        config_name = "beta.jsonc"
        db_name = "dbBeta.sqlite3"
    else:
        config_name = "config.jsonc"
        db_name = "db.sqlite3"

    db_migration_setup(db_name)
    db_file = Path(DATA_DIR, db_name)
    data_filenames.insert(0, config_name)

    for filename in data_filenames:
        with open(Path(CONFIG_DIR, filename), encoding="UTF-8") as json_file:
            bot_data.update(commentjson.load(json_file))
    bot.__dict__.update(bot_data)

    async with aiosqlite.connect(db_file) as conn, bot:
        bot.database_conn = conn

        await create_database_schema(conn)
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
