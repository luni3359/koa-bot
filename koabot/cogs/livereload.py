"""Live reloading
https://gist.github.com/AXVin/08ed554a458fc7aee4da162f4c53d086"""
# pylint: disable=no-member,unused-argument
import os
from datetime import datetime

from discord.ext import commands, tasks

from koabot.core.utils import calculate_sha1, path_from_extension
from koabot.kbot import KBot


class ReloadableExt():
    def __init__(self, extension: str = None) -> None:
        self.last_modified_time: float
        self.file_hash: str

        if extension:
            path = path_from_extension(extension)
            self.last_modified_time = os.path.getmtime(path)
            self.file_hash = calculate_sha1(path)


# put your extension names in this list
# if you don't want them to be reloaded
IGNORE_EXTENSIONS: list[str] = []


class LiveReload(commands.Cog):
    """Cog for reloading extensions as soon as the file is edited"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.enabled = True
        self.extension_list: dict[str, ReloadableExt] = {}

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
            modified_time = os.path.getmtime(path)

            if extension not in self.extension_list:
                new_ext = ReloadableExt()
                new_ext.last_modified_time = modified_time
                new_ext.file_hash = calculate_sha1(path)
                self.extension_list[extension] = new_ext

            current_ext = self.extension_list[extension]

            if current_ext.last_modified_time == modified_time:
                continue

            if (sha1_hash := calculate_sha1(path)) == current_ext.file_hash:
                print(f"Unable to reload '{extension}' (Hashes are identical)")
                current_ext.last_modified_time = modified_time
                continue

            try:
                await self.bot.reload_extension(extension)
            except commands.ExtensionNotLoaded:
                continue
            except commands.ExtensionError:
                print(f"Unable to reload '{extension}'")
            else:
                print(f"Reloaded '{extension}' @ {datetime.today()}")
            finally:
                current_ext.last_modified_time = modified_time
                current_ext.file_hash = sha1_hash

    @live_reload_loop.before_loop
    async def cache_last_modified_time(self):
        # Mapping = {extension: ReloadableExt}
        for extension in self.bot.extensions.keys():
            if extension in IGNORE_EXTENSIONS:
                continue
            self.extension_list[extension] = ReloadableExt(extension)

    @commands.hybrid_command(name="reload", hidden=True)
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

    @commands.hybrid_command(name="autoreload", hidden=True)
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
