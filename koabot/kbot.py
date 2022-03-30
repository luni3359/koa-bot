"""The main bot class"""
import os
import sqlite3
import timeit
from datetime import datetime
from enum import Enum
from pathlib import Path

from discord.ext import commands


class BaseDirectory(Enum):
    BOT_DIRNAME = 1
    SOURCE_DIR = 2
    PROJECT_DIR = 3
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

        self.BOT_DIRNAME: str = None
        self.SOURCE_DIR: str = None
        self.PROJECT_DIR: Path = None
        self.DATA_DIR: str = None
        self.CONFIG_DIR: str = None
        self.CACHE_DIR: str = None

    async def setup_hook(self):
        print(f'Logged in to Discord  [{datetime.utcnow().replace(microsecond=0)} (UTC+0)]')

        # TODO: For some reason `self.change_presence` is None when this executes
        # Change play status to something fitting
        # await self.change_presence(activity=discord.Game(name=self.get_cog('BotStatus').get_quote('playing_status')))

    def set_base_directory(self, directory: BaseDirectory, value: str | Path) -> None:
        if isinstance(value, Path):
            value = str(value)

        match directory:
            case BaseDirectory.SOURCE_DIR:
                self.SOURCE_DIR = value
            case BaseDirectory.BOT_DIRNAME:
                self.BOT_DIRNAME = value
            case BaseDirectory.PROJECT_DIR:
                self.PROJECT_DIR = value
            case BaseDirectory.DATA_DIR:
                self.DATA_DIR = value
            case BaseDirectory.CONFIG_DIR:
                self.CONFIG_DIR = value
            case BaseDirectory.CACHE_DIR:
                self.CACHE_DIR = value

    async def load_all_extensions(self, path: str) -> None:
        """Recursively load all cogs in the project"""
        print("Loading cogs in project...")

        start_load_time = timeit.default_timer()
        cog_prefix = "koabot.cogs"
        cog_paths: list[str] = []

        for p, _, f in os.walk(path):
            for file in f:
                if file.endswith(".py"):
                    container_dir = p.replace(path, '').replace('/', '.')
                    (filename, _) = os.path.splitext(file)

                    if filename == "__init__":
                        continue

                    cog_path = cog_prefix + container_dir + '.' + filename
                    cog_paths.append(cog_path)

        dropped_cogs = 0
        for ext in cog_paths:
            try:
                print(f"Loading \"{ext}\"...".ljust(40), end='\r')
                await self.load_extension(ext)
            except commands.errors.ExtensionFailed as e:
                dropped_cogs += 1
                print(e)
                print(f"Failed to load \"{ext}\".")

        time_to_finish = timeit.default_timer() - start_load_time

        if dropped_cogs == 0:
            log_msg = f"Finished loading {len(cog_paths)} cogs in {time_to_finish:0.2f}s."
        else:
            log_msg = f"WARNING: Only {len(cog_paths)-dropped_cogs} out of {len(cog_paths)} cogs loaded successfully (in {time_to_finish:0.2f}s)."

        print(log_msg.ljust(40))
