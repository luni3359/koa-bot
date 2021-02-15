"""Bot-related commands and features"""
import asyncio
import random
import re
import subprocess
from datetime import datetime

from discord.ext import commands


class BotStatus(commands.Cog):
    """BotStatus class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='temperature', aliases=['temp'])
    async def report_bot_temp(self, ctx):
        """Show the bot's current temperature"""

        temp_commands = ['vcgencmd measure_temp', 'sensors']
        for cmd in temp_commands:
            cmd_parts = cmd.split()
            temp_command = cmd_parts[0]

            try:
                current_temp = subprocess.run(cmd_parts, stdout=subprocess.PIPE, check=True, universal_newlines=True)
                print(f'Using "{temp_command}".')
                break
            except FileNotFoundError:
                print(f'"{temp_command}" is missing in system.')

        try:
            if temp_command == 'vcgencmd':
                cpu_temp = re.findall(r'([0-9]+\.[0-9]?)\'C', current_temp.stdout)[0]
            elif temp_command == 'sensors':
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

            print(f'CPU Temp: {cpu_temp:0.1f} °C')
            await ctx.send(f"I'm at {cpu_temp:0.1f} °C.")
        except NameError:
            print('Unable to report temperature.')
            await ctx.send("I can't get the temperature...")

    @commands.command(name='last')
    async def talk_status(self, ctx):
        """Mention a brief summary of the last used channel"""
        await ctx.send(f'Last channel: {self.bot.last_channel}\nCurrent count there: {self.bot.last_channel_message_count}')

    @commands.command()
    async def uptime(self, ctx):
        """Mention the current uptime"""

        delta_uptime = datetime.utcnow() - self.bot.launch_time
        (hours, remainder) = divmod(int(delta_uptime.total_seconds()), 3600)
        (minutes, seconds) = divmod(remainder, 60)
        (days, hours) = divmod(hours, 24)
        await ctx.send(f"I've been running for {days} days, {hours} hours, {minutes} minutes and {seconds} seconds.")

    @commands.command()
    async def version(self, ctx):
        """Show bot's version"""
        commit = subprocess.check_output(['git', 'describe', '--always']).strip()
        await ctx.send(f"On commit ``{commit.decode('utf-8')}``.")

    async def typing_a_message(self, ctx, **kwargs):
        """Make Koakuma seem alive with a 'is typing' delay

        Keywords:
            content::str
                Message to be said.
            embed::discord.Embed
                Self-explanatory. Default is None.
            rnd_duration::list or int
                A list with two int values of what's the least that should be waited for to the most, chosen at random.
                If provided an int the 0 will be assumed at the start.
            min_duration::int
                The amount of time that will be waited regardless of rnd_duration.
        """

        content = kwargs.get('content')
        embed = kwargs.get('embed')
        rnd_duration = kwargs.get('rnd_duration')
        min_duration = kwargs.get('min_duration', 0)

        if isinstance(rnd_duration, int):
            rnd_duration = [0, rnd_duration]

        async with ctx.typing():
            if rnd_duration:
                time_to_wait = random.randint(rnd_duration[0], rnd_duration[1])
                if time_to_wait < min_duration:
                    time_to_wait = min_duration
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


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(BotStatus(bot))
