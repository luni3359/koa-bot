"""Live reloading
https://gist.github.com/AXVin/08ed554a458fc7aee4da162f4c53d086"""
# pylint: disable=no-member,unused-argument
import os
from datetime import datetime
from pathlib import Path

from discord.ext import commands, tasks

from koabot.kbot import KBot

# put your extension names in this list
# if you don't want them to be reloaded
IGNORE_EXTENSIONS: list[str] = []


def path_from_extension(extension: str) -> Path:
    return Path(extension.replace('.', os.sep)+'.py')


class LiveReload(commands.Cog):
    """Cog for reloading extensions as soon as the file is edited"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.enabled = True
        self.last_modified_time = {}

    async def cog_load(self):
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
                print(f"Unable to reload '{extension}'")
            else:
                print(f"Reloaded '{extension}' @ {datetime.today()}")

            finally:
                self.last_modified_time[extension] = time

    @live_reload_loop.before_loop
    async def cache_last_modified_time(self):
        # Mapping = {extension: timestamp}
        for extension in self.bot.extensions.keys():
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)
            self.last_modified_time[extension] = time

    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def reload_extension(self, ctx: commands.Context, *, extension: str):
        """Reloads a module"""
        if extension == "all":
            return

        try:
            await self.bot.unload_extension(extension)
            await self.bot.load_extension(extension)
        except Exception as e:
            await ctx.reply(f"{type(e).__name__}: {e}", mention_author=False)
        else:
            await ctx.reply(f"Reloaded '{extension}' @ {datetime.today()}", mention_author=False)

    @commands.command(name="autoreload", hidden=True)
    @commands.is_owner()
    async def autoreload_extensions(self, ctx: commands.Context, mode: str):
        """Toggles autoreload on or off"""
        print(f"Turning autoreload {mode}...")

        if mode == "on":
            try:
                if self.enabled:
                    raise ValueError()
                self.live_reload_loop.start()
            except (RuntimeError, ValueError):
                print("Autoreload is already on.")

            self.enabled = True
        elif mode == "off":
            try:
                if not self.enabled:
                    raise ValueError()
                self.live_reload_loop.stop()
            except ValueError:
                print("Autoreload is already off.")

            self.enabled = False


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(LiveReload(bot))
