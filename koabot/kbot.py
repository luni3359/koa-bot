"""The main bot class"""
import os
import sqlite3
import timeit
from datetime import datetime
from enum import Enum
from pathlib import Path

from discord.ext import commands


class BaseDirectory(Enum):
    PROJECT_NAME = 1
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

        self.PROJECT_NAME: str = None
        self.SOURCE_DIR: Path = None
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
        match directory:
            case BaseDirectory.SOURCE_DIR:
                self.SOURCE_DIR = value
            case BaseDirectory.PROJECT_NAME:
                self.PROJECT_NAME = value
            case BaseDirectory.PROJECT_DIR:
                self.PROJECT_DIR = value
            case BaseDirectory.DATA_DIR:
                self.DATA_DIR = value
            case BaseDirectory.CONFIG_DIR:
                self.CONFIG_DIR = value
            case BaseDirectory.CACHE_DIR:
                self.CACHE_DIR = value

    async def load_all_extensions(self) -> None:
        """Recursively load all cogs in the project"""
        print("Loading cogs in project...")

        extension_dirs = [Path(self.SOURCE_DIR, "core"), Path(self.SOURCE_DIR, "cogs")]

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
