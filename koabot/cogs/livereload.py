"""Live reloading
https://gist.github.com/AXVin/08ed554a458fc7aee4da162f4c53d086"""
# pylint: disable=no-member
import os
import pathlib

from discord.ext import commands, tasks

from koabot.kbot import KBot

# put your extension names in this list
# if you don't want them to be reloaded
IGNORE_EXTENSIONS: list[str] = []


def path_from_extension(extension: str) -> pathlib.Path:
    return pathlib.Path(extension.replace('.', os.sep)+'.py')


class LiveReload(commands.Cog):
    """Cog for reloading extensions as soon as the file is edited"""

    def __init__(self, bot: KBot):
        self.bot = bot
        self.live_reload_loop.start()

    async def cog_unload(self):
        self.live_reload_loop.stop()

    @tasks.loop(seconds=3)
    async def live_reload_loop(self):
        for extension in list(self.bot.extensions.keys()):
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)

            try:
                if self.last_modified_time[extension] == time:
                    continue
            except KeyError:
                self.last_modified_time[extension] = time

            try:
                await self.bot.reload_extension(extension)
            except commands.ExtensionNotLoaded:
                continue
            except commands.ExtensionError:
                print(f"Couldn't reload extension: {extension}")
            else:
                print(f"Reloaded extension: {extension}")
            finally:
                self.last_modified_time[extension] = time

    @live_reload_loop.before_loop
    async def cache_last_modified_time(self):
        self.last_modified_time = {}
        # Mapping = {extension: timestamp}
        for extension in self.bot.extensions.keys():
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)
            self.last_modified_time[extension] = time


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(LiveReload(bot))
