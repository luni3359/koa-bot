"""Bot-related commands and features"""
import asyncio
import random
import re
import subprocess
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from single_source import get_version

from koabot import koakuma


class BotStatus(commands.Cog):
    """BotStatus class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='temperature', aliases=['temp'])
    async def report_bot_temp(self, ctx: commands.Context, /):
        """Show the bot's current temperature"""

        temperature_cmds = ['vcgencmd measure_temp', 'sensors']
        for cmd in temperature_cmds:
            cmd_parts = cmd.split()
            temperature_cmd = cmd_parts[0]

            try:
                current_temp = subprocess.run(cmd_parts, stdout=subprocess.PIPE, check=True, universal_newlines=True)
                print(f'Using "{temperature_cmd}".')
                break
            except FileNotFoundError:
                print(f'"{temperature_cmd}" is missing in system.')

        try:
            match temperature_cmd:
                case 'vcgencmd':
                    cpu_temp = re.findall(r'([0-9]+\.[0-9]?)\'C', current_temp.stdout)[0]
                case 'sensors':
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
            await ctx.send(f"I'm at {cpu_temp:0.1f} °C.")
        except NameError:
            print("Unable to report temperature.")
            await ctx.send("I can't get the CPU's temperature...")

    @commands.command(name='last')
    async def talk_status(self, ctx: commands.Context, /):
        """Mention a brief summary of the last used channel"""
        await ctx.send(f'Last channel: {self.bot.last_channel}\nCurrent count there: {self.bot.last_channel_message_count}')

    @commands.command()
    async def uptime(self, ctx: commands.Context, /):
        """Mention the current uptime"""

        delta_uptime: timedelta = datetime.utcnow() - self.bot.launch_time
        (hours, remainder) = divmod(int(delta_uptime.total_seconds()), 3600)
        (minutes, seconds) = divmod(remainder, 60)
        (days, hours) = divmod(hours, 24)
        await ctx.send(f"I've been running for {days} days, {hours} hours, {minutes} minutes and {seconds} seconds.")

    @commands.command()
    async def version(self, ctx: commands.Context, /):
        """Show bot's version"""
        version = get_version(koakuma.BOT_DIRNAME, koakuma.PROJECT_DIR)
        await ctx.send(f"On version `{version}`.")

    async def typing_a_message(self, ctx: commands.Context, /, **kwargs):
        """Make Koakuma seem alive with a 'is typing' delay

        Keywords:
            content::str
                Message to be said.
            embed::discord.Embed
                Self-explanatory. Default is None.
            rnd_duration::list | int
                A list with two int values of what's the least that should be waited for to the most, chosen at random.
                If provided an int the 0 will be assumed at the start.
            min_duration::int
                The amount of time that will be waited regardless of rnd_duration.
        """

        content: str = kwargs.get('content')
        embed: discord.Embed = kwargs.get('embed')
        rnd_duration: list | int = kwargs.get('rnd_duration')
        min_duration: int = kwargs.get('min_duration', 0)

        if isinstance(rnd_duration, int):
            rnd_duration = [0, rnd_duration]

        async with ctx.typing():
            if rnd_duration:
                time_to_wait = max(min_duration, random.randint(rnd_duration[0], rnd_duration[1]))
                await asyncio.sleep(time_to_wait)
            else:
                await asyncio.sleep(min_duration)

            if embed is not None:
                if content:
                    await ctx.send(content, embed=embed)
                else:
                    await ctx.send(embed=embed)
            else:
                await ctx.send(content)

    def get_quote(self, key: str, /, **kwargs) -> str:
        """Get a quote from Koakuma's file of things to say"""
        if kwargs:
            return random.choice(self.bot.quotes[key]).format(**kwargs)

        return random.choice(self.bot.quotes[key])


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(BotStatus(bot))
