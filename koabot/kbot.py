"""The main bot class"""
import os
import sqlite3
import timeit
from datetime import datetime
from enum import Enum
from pathlib import Path

import discord
from discord.ext import commands


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
        self.sqlite_conn: sqlite3.Connection = None
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
        print(f'Logged in to Discord  [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')
        self.add_check(debug_check)
        # TODO: For some reason `self.change_presence` is None when this executes
        # Change play status to something fitting
        # await self.change_presence(activity=discord.Game(name=self.get_cog('BotStatus').get_quote('playing_status')))

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

                    if filename == "__init__":
                        continue

                    relative_path = child.relative_to(self.PROJECT_DIR)
                    path_as_import = str(relative_path.with_suffix('')).replace(os.sep, '.')
                    module_list.append(path_as_import)

        dropped_cogs = 0
        for module in module_list:
            try:
                print(f"Loading \"{module}\"...".ljust(40), end='\r')
                await self.load_extension(module)
            except commands.errors.ExtensionFailed as e:
                dropped_cogs += 1
                print(e)
                print(f"Failed to load \"{module}\".")
            except commands.errors.NoEntryPointError as e:
                print(f"Skipping \"{module}\" (not a module)")

        time_to_finish = timeit.default_timer() - start_load_time

        if dropped_cogs == 0:
            log_msg = f"Finished loading {len(module_list)} cogs in {time_to_finish:0.2f}s."
        else:
            log_msg = f"WARNING: Only {len(module_list)-dropped_cogs} out of {len(module_list)} cogs loaded successfully (in {time_to_finish:0.2f}s)."

        print(log_msg.ljust(40))


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
