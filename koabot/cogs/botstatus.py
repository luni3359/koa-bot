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
                print('Using "%s".' % temp_command)
                break
            except FileNotFoundError:
                print('"%s" is missing in system.' % temp_command)

        try:
            if temp_command == 'vcgencmd':
                cpu_temp = re.findall(r'([0-9]+\.[0-9]?)\'C', current_temp.stdout)
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

            print('CPU Temp: %f °C' % cpu_temp)
            await ctx.send('I\'m at %0.1f °C.' % cpu_temp)
        except NameError:
            print('Unable to report temperature.')
            await ctx.send('I can\'t get the temperature...')

    @commands.command(name='last')
    async def talk_status(self, ctx):
        """Mention a brief summary of the last used channel"""
        await ctx.send('Last channel: %s\nCurrent count there: %s' % (self.bot.last_channel, self.bot.last_channel_message_count))

    @commands.command()
    async def uptime(self, ctx):
        """Mention the current uptime"""

        delta_uptime = datetime.utcnow() - self.bot.launch_time
        (hours, remainder) = divmod(int(delta_uptime.total_seconds()), 3600)
        (minutes, seconds) = divmod(remainder, 60)
        (days, hours) = divmod(hours, 24)
        await ctx.send('I\'ve been running for %i days, %i hours, %i minutes and %i seconds.' % (days, hours, minutes, seconds))

    @commands.command()
    async def version(self, ctx):
        """Show bot's version"""

        commit = subprocess.check_output(['git', 'describe', '--always']).strip()
        await ctx.send('On commit %s.' % commit.decode('utf-8'))


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(BotStatus(bot))
