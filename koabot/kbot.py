"""The main bot class"""
import os
import re
import timeit
from datetime import datetime
from enum import Enum
from pathlib import Path

import aiosqlite
import discord
from discord.ext import commands
from tqdm import tqdm


class BaseDirectory(Enum):
    PROJECT_NAME = 1
    PROJECT_DIR = 2
    MODULE_DIR = 3
    DATA_DIR = 4
    CONFIG_DIR = 5
    CACHE_DIR = 6


class KBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_mode: bool = None
        self.database_conn: aiosqlite.Connection
        self.launch_time: datetime = None
        self.connect_time: datetime = None
        self.isconnected: bool = False

        self.PROJECT_NAME: str = None
        self.PROJECT_DIR: Path = None
        self.MODULE_DIR: Path = None
        self.DATA_DIR: Path = None
        self.CONFIG_DIR: Path = None
        self.CACHE_DIR: Path = None

    async def setup_hook(self):
        self.add_check(debug_check)
        self.loop.create_task(self.run_once_when_ready())

    async def run_once_when_ready(self) -> None:
        await self.wait_until_ready()
        await self.populate_server_db()

    def set_base_directory(self, directory: BaseDirectory, value: str | Path) -> None:
        match directory:
            case BaseDirectory.PROJECT_NAME:
                self.PROJECT_NAME = value  # this is the only string value
            case BaseDirectory.PROJECT_DIR:
                self.PROJECT_DIR = value
            case BaseDirectory.MODULE_DIR:
                self.MODULE_DIR = value
            case BaseDirectory.DATA_DIR:
                self.DATA_DIR = value
            case BaseDirectory.CONFIG_DIR:
                self.CONFIG_DIR = value
            case BaseDirectory.CACHE_DIR:
                self.CACHE_DIR = value

    async def load_all_extensions(self) -> None:
        """Recursively load all cogs in the project"""
        print("Loading cogs in project...")

        extension_dirs = [Path(self.MODULE_DIR, "core"), Path(self.MODULE_DIR, "cogs")]

        start_load_time = timeit.default_timer()
        module_list: list[str] = []

        for ext_dir in extension_dirs:
            for child in ext_dir.rglob('*'):
                if child.suffix == ".py":
                    filename = child.stem

                    if re.search(r'__.*__', filename):
                        # file is __init__ or __main__
                        continue

                    relative_path = child.relative_to(self.PROJECT_DIR)
                    path_as_import = str(relative_path.with_suffix('')).replace(os.sep, '.')
                    module_list.append(path_as_import)

        skipped_cogs: int = 0
        dropped_cogs: list = []

        for module in tqdm(module_list, ncols=75):
            try:
                # print(f"Loading \"{module}\"...".ljust(40), end='\r')
                await self.load_extension(module)
            except commands.errors.ExtensionFailed as e:
                dropped_cogs.append([module, e])
                # print(e)
                # print(f"Failed to load \"{module}\".")
            except commands.errors.NoEntryPointError as e:
                skipped_cogs += 1
                # print(f"Skipping \"{module}\" (not a module)")

        time_to_finish = timeit.default_timer() - start_load_time
        loaded_cogs = len(module_list) - skipped_cogs

        if not dropped_cogs:
            log_msg = f"Finished loading {loaded_cogs} cogs in {time_to_finish:0.2f}s."
        else:
            log_msg = f"WARNING: Only {loaded_cogs - len(dropped_cogs)} out of {loaded_cogs} cogs loaded successfully (in {time_to_finish:0.2f}s)."

            for name, error in dropped_cogs:
                log_msg += f"\nModule: {name}\n{error}"

        print(log_msg)

    async def populate_server_db(self) -> None:
        conn = self.database_conn
        srv_query = "INSERT INTO discordServer (serverDId, serverName, dateFirstSeen) VALUES (?, ?, ?)"
        usr_query = "INSERT INTO discordUser (userDid, userName, dateFirstSeen) VALUES (?, ? ,?)"
        srv_usr_query = "INSERT INTO discordServerUser (userId, serverId, userNickname) VALUES (?, ?, ?)"

        async with conn.cursor() as cursor:
            for guild in self.guilds:
                guild_id: int
                try:
                    await cursor.execute(srv_query, (guild.id, guild.name, datetime.now()))
                    guild_id = cursor.lastrowid
                    await conn.commit()
                except aiosqlite.IntegrityError:
                    # print(f"Guild '{guild.name}' is already in the database")
                    await cursor.execute("SELECT serverId FROM discordServer WHERE serverDId = ?", (guild.id, ))
                    guild_id, = await cursor.fetchone()

                for member in guild.members:
                    member_id: int
                    try:
                        await cursor.execute(usr_query, (member.id, member.name, datetime.now()))
                        member_id = cursor.lastrowid
                    except aiosqlite.IntegrityError:
                        # print(f"Member '{member.name}' is already in the database")
                        await cursor.execute("SELECT userId FROM discordUser WHERE userDId = ?", (member.id, ))
                        member_id, = await cursor.fetchone()  # unpacking tuple

                    try:
                        await cursor.execute(srv_usr_query, (member_id, guild_id, member.nick))
                        await conn.commit()
                    except aiosqlite.IntegrityError:
                        # print("This user-guild pair already exists")
                        ...

    async def add_member_to_db(self, member: discord.Member) -> None:
        conn = self.database_conn
        srv_query = "INSERT INTO discordServer (serverDId, serverName, dateFirstSeen) VALUES (?, ?, ?)"
        usr_query = "INSERT INTO discordUser (userDid, userName, dateFirstSeen) VALUES (?, ? ,?)"
        srv_usr_query = "INSERT INTO discordServerUser (userId, serverId, userNickname) VALUES (?, ?, ?)"
        async with conn.cursor() as cursor:
            guild = member.guild
            try:
                await cursor.execute(srv_query, (guild.id, guild.name, datetime.now()))
                await conn.commit()
            except aiosqlite.IntegrityError:
                # print(f"Guild '{guild.name}' is already in the database")
                ...

            try:
                await cursor.execute(usr_query, (member.id, member.name, datetime.now()))
            except aiosqlite.IntegrityError:
                # print(f"Member '{member.name}' is already in the database")
                ...

            try:
                await cursor.execute(srv_usr_query, (member.id, guild.id, member.nick))
                await conn.commit()
            except aiosqlite.IntegrityError:
                # print("This user-guild pair already exists")
                ...


async def debug_check(ctx: commands.Context) -> bool:
    """Disable live instance for specific users if a beta instance is running"""
    # ignore everything in DMs
    if ctx.guild is None:
        return False

    # if the author is not a debug user
    if ctx.author.id not in ctx.bot.testing['debug_users']:
        return not ctx.bot.debug_mode

    if not ctx.bot.debug_mode:
        beta_bot_id = ctx.bot.koa['discord_user']['beta_id']
        beta_bot: discord.Member = ctx.guild.get_member(beta_bot_id)

        # if the beta bot is online
        if beta_bot and beta_bot.status == discord.Status.online:
            return False

    return True
