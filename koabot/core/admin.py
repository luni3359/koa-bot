"""Commands for managing the bot"""
import re
import subprocess

from discord.ext import commands

from koabot.kbot import KBot


class Admin(commands.Cog):
    def __init__(self, bot: KBot) -> None:
        self.bot: KBot = bot

    @commands.hybrid_command(name="temperature", aliases=['temp'], hidden=True)
    @commands.is_owner()
    async def server_temperature(self, ctx: commands.Context, /):
        """Show the bot's current temperature"""
        temperature_cmd = None
        for cmd in ["vcgencmd measure_temp", "sensors"]:
            cmd_parts = cmd.split()
            temperature_cmd = cmd_parts[0]

            try:
                current_temp = subprocess.run(cmd_parts, stdout=subprocess.PIPE, check=True, universal_newlines=True)
                print(f"Using \"{temperature_cmd}\".")
                break
            except FileNotFoundError:
                print(f"\"{temperature_cmd}\" is missing in system.")

        if not temperature_cmd:
            print("Unable to report temperature.")
            await ctx.reply("I can't get the CPU's temperature...", mention_author=False)

        match temperature_cmd:
            case "vcgencmd":
                cpu_temp = re.findall(r'([0-9]+\.[0-9]?)\'C', current_temp.stdout)[0]
            case "sensors":
                cpu_found = False
                adapter_found = False

                for line in current_temp.stdout.splitlines():
                    if re.search(r'coretemp', line):
                        cpu_found = True
                        continue

                    if re.search(r'Adapter', line):
                        if not cpu_found:
                            continue

                        adapter_found = True
                        continue

                    if re.search(r'Package id|Core 0', line):
                        if not cpu_found or not adapter_found:
                            continue

                        cpu_temp = re.findall(r'([0-9]+\.[0-9]?)°C', line)[0]
                        break

        cpu_temp = float(cpu_temp)

        print(f"CPU Temp: {cpu_temp:0.1f} °C")
        await ctx.reply(f"I'm at {cpu_temp:0.1f} °C.", mention_author=False)

    @commands.hybrid_command(name="last", hidden=True)
    @commands.is_owner()
    async def talk_status(self, ctx: commands.Context, /):
        """Mention a brief summary of the last used channel"""
        await ctx.reply(f"Last channel: {self.bot.last_channel}\nCurrent count there: {self.bot.last_channel_message_count}", mention_author=False)

    @commands.hybrid_command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync_slash_commands(self, ctx: commands.Context):
        """Sync all commands with Discord"""
        for guild in ctx.bot.guilds:
            ctx.bot.tree.copy_global_to(guild=guild)
            await ctx.bot.tree.sync(guild=guild)

        await ctx.reply("Synchronized all commands!", mention_author=False)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Admin(bot))
