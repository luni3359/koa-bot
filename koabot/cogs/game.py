"""Fun games that are barely playable, yay!"""
import random
import re
from heapq import nlargest, nsmallest

from discord.ext import commands
from num2words import num2words

from koabot.patterns import DICE_PATTERN


class RollMatch:
    """Roll object helper"""

    def __init__(self, dice_match: re.Match):
        self.type: str = None
        self.sign: str = dice_match.group(1)
        self.quantity: int = dice_match.group(2)
        self.pips: int = dice_match.group(3)
        self.keep = dice_match.group(4)
        self.raw_points: int = dice_match.group(5)
        self.limited_quantity = False

        if not self.quantity:
            self.quantity = 1
        else:
            self.quantity = int(self.quantity)
            if self.quantity > 100:
                self.limited_quantity = True

            self.quantity = min(self.quantity, 100)

        if not self.pips:
            self.type = "points"
            self.pips = 0
        else:
            self.type = "roll"
            self.pips = int(self.pips)

        if not self.raw_points:
            self.raw_points = 0

        if not self.sign:
            self.sign = '+'

        if self.sign == '+':
            self.raw_points = int(self.raw_points)
        else:
            self.raw_points = -int(self.raw_points)


class Game(commands.Cog):
    """Commands to play with"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['r'])
    async def roll(self, ctx: commands.Context, *, roll_string: str):
        """Rolls one or many dice"""
        matches_found = []
        roll_count = 0
        i = 0
        while i < len(roll_string):
            if roll_string[i] == ' ':
                i += 1
                continue

            pattern_match = DICE_PATTERN.match(roll_string, i)

            if pattern_match:
                match = RollMatch(pattern_match)

                if match.pips and match.quantity > 0:
                    roll_count += match.quantity
                elif match.type == "roll":
                    roll_count += 1

                matches_found.append(match)
                i = pattern_match.end()
                continue

            return await ctx.send("Invalid syntax!")

        # there should always be at least one roll - never do raw math
        if roll_count == 0:
            return await ctx.send("Please roll something!")

        total_sum = 0
        logic_string = ""
        die_or_dice = roll_count > 1 and 'dice' or 'die'
        message = f">>> {ctx.author.mention} rolled the {die_or_dice}.\n"

        for i, match in enumerate(matches_found):
            match: RollMatch = match

            if match.type == "points":
                if match.sign == '+':
                    message += "Add "
                else:
                    message += "Subtract "

                s_or_no_s = (abs(match.raw_points) > 1 or match.raw_points == 0) and 's' or ''

                message += f"{abs(match.raw_points)} point{s_or_no_s}.\n"
                if i == 0 and match.sign == '+':
                    logic_string += f"__{match.raw_points}__ "
                else:
                    logic_string += f"{match.sign} __{abs(match.raw_points)}__ "

                total_sum += match.raw_points
                continue

            dice_or_die = match.quantity != 1 and 'dice' or 'die'

            if match.limited_quantity:
                message += '\*'

            if match.quantity == 0 or match.pips == 0:
                message += f"{num2words(match.quantity).capitalize()} {match.pips}-sided {dice_or_die}. Nothing to roll.  **0.**\n"
                continue

            roll_list = []

            if match.keep:
                if int(match.keep[2:]) != 0:
                    keep_type = match.keep[1]
                    keep_length = int(match.keep[2:])
                    keep_list = []
                    overkeep = False

                    if keep_length > match.quantity:
                        keep_length = match.quantity
                        overkeep = True
                else:
                    match.keep = ''

            if match.sign == '+':
                message += f"{num2words(match.quantity).capitalize()}"
            else:
                message += f"Minus {num2words(match.quantity)}"

            message += f" {match.pips}-sided {dice_or_die} for a "

            for j in range(0, match.quantity):
                die_roll = random.randint(1, match.pips)
                roll_list.append(die_roll)

                if match.keep:
                    keep_list.append(die_roll)

                    if len(keep_list) >= keep_length:
                        if keep_type == 'l':
                            keep_list = nsmallest(keep_length, keep_list)
                        elif keep_type == 'h':
                            keep_list = nlargest(keep_length, keep_list)

                # Final die in group throw
                if j == match.quantity - 1:
                    if match.quantity == 1:
                        message += f'{die_roll}.'
                    else:
                        message += f'and a {die_roll}.'

                    if match.keep:
                        if keep_type == 'l':
                            keep_type = 'lowest'
                        elif keep_type == 'h':
                            keep_type = 'highest'
                        message += f'\nKeep the {keep_type} '

                        if keep_length > 1:
                            message += f'{num2words(keep_length)}' + (overkeep and '*' or '') + ': ' + ', '.join(
                                map(str, keep_list[0:keep_length-1])) + f' and a {keep_list[keep_length-1]}.'
                        else:
                            message += f'number: {keep_list[0]}.'

                        if i != 0 or match.sign != '+':
                            logic_string += f"{match.sign} "

                        if len(keep_list) > 1 and (len(matches_found) > 1 or match.sign != "+"):
                            logic_string += f"__({' + '.join(map(str, keep_list))})__ "
                        else:
                            logic_string += f"__{' + '.join(map(str, keep_list))}__ "

                        if match.sign == '+':
                            total_sum += sum(keep_list)
                        else:
                            total_sum -= sum(keep_list)

                    message += '\n'
                elif j == match.quantity - 2:
                    message += f'{die_roll} '
                else:
                    message += f'{die_roll}, '

                if not match.keep:
                    if match.sign == '+':
                        total_sum += die_roll
                    else:
                        total_sum -= die_roll

            if not match.keep:
                if i != 0 or match.sign != '+':
                    logic_string += f"{match.sign} "

                if len(roll_list) > 1 and (len(matches_found) > 1 or match.sign != "+"):
                    logic_string += f"__({' + '.join(map(str, roll_list))})__ "
                else:
                    logic_string += f"__{' + '.join(map(str, roll_list))}__ "

        if logic_string:
            message += f"{logic_string}\n"

        message += f"For a total of **{total_sum}.**"

        await ctx.send(message[0:2000])

    @roll.error
    async def roll_error(self, ctx: commands.Context, exception: commands.CommandError):
        """Roll exception handler"""
        if isinstance(exception, commands.MissingRequiredArgument):
            return await ctx.send("Please specify what you want to roll.")


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Game(bot))
