"""Fun games that are barely playable, yay!"""
import random
import re
from heapq import nlargest, nsmallest

from discord.ext import commands
from num2words import num2words

from koabot.patterns import DICE_PATTERN


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, *dice):
        """Rolls one or many dice"""

        if len(dice) < 1:
            await ctx.send('Please specify what you want to roll.')
            return

        dice_matches = re.findall(DICE_PATTERN, ' '.join(dice))

        if not dice_matches:
            roll_suggestions = [
                f"・ **d{random.randint(3,12)}**",
                f"・ **{random.randint(2,5)}d{random.randint(3,6)} {random.choice(['-','+'])}{random.randint(1,5)}**",
                f"・ **{random.randint(2,5)}d{random.randint(3,6)} {random.randint(2,5)}d{random.randint(3,6)} {random.choice(['-','+'])}{random.randint(1,5)} {random.randint(2,5)}d{random.randint(3,6)} {random.choice(['-','+'])}{random.randint(1,5)}**",
            ]
            apology = "Sorry, I can't do that... Please try with any of the following examples:\n"

            random.shuffle(roll_suggestions)

            await ctx.send(apology + '\n'.join(roll_suggestions))
            return

        dice_single_or_many = len(dice_matches) > 1 or (dice_matches[0][0] and int(dice_matches[0][0]) > 1)
        message = f">>> {ctx.author.mention} rolled the {dice_single_or_many and 'dice' or 'die'}.\n"
        pip_sum = 0

        for match in dice_matches:
            quantity = 1
            pips = match[1] and int(match[1]) or 0
            bonus_points = match[2] and int(match[2]) or 0
            keep = match[3] or ''

            if match[0]:
                quantity = int(match[0])
                if quantity > 10000:
                    message += '\*'

                quantity = min(quantity, 10000)

            if quantity == 0 or pips == 0:
                message += f"{num2words(quantity).capitalize()} {pips}-sided {quantity != 1 and 'dice' or 'die'}. Nothing to roll."
                if bonus_points:
                    pip_sum += bonus_points

                    if bonus_points > 0:
                        message += f' +{bonus_points}'
                    else:
                        message += f' {bonus_points}'
                else:
                    message += ' **0.**'

                message += '\n'
                continue

            if keep:
                if int(keep[2:]) != 0:
                    keep_type = keep[1]
                    keep_length = int(keep[2:])
                    keep_list = []
                else:
                    keep = ''

            message += f"{num2words(quantity).capitalize()} {pips}-sided {quantity != 1 and 'dice' or 'die'} for a "

            for i in range(0, quantity):
                die_roll = random.randint(1, pips)

                if keep:
                    keep_list.append(die_roll)

                    if len(keep_list) >= keep_length:
                        if keep_type == 'l':
                            keep_list = nsmallest(keep_length, keep_list)
                        elif keep_type == 'h':
                            keep_list = nlargest(keep_length, keep_list)

                if i == quantity - 1:
                    if quantity == 1:
                        message += f'{die_roll}.'
                    else:
                        message += f'and a {die_roll}.'

                    if bonus_points:
                        pip_sum += bonus_points

                        if bonus_points > 0:
                            message += f' +{bonus_points}'
                        else:
                            message += f' {bonus_points}'

                    if keep:
                        if keep_type == 'l':
                            keep_type = 'lowest'
                        elif keep_type == 'h':
                            keep_type = 'highest'
                        message += f'\nKeep the {keep_type} '
        
                        if keep_length > 1:
                            message += f'{num2words(keep_length)}: ' + ', '.join(map(str, keep_list[0:keep_length-1])) + f' and a {keep_list[keep_length-1]}.'
                        else:
                            message += f'number: {keep_list[0]}.'
                        pip_sum += sum(keep_list)

                    message += '\n'
                elif i == quantity - 2:
                    message += f'{die_roll} '
                else:
                    message += f'{die_roll}, '

                if not keep:
                    pip_sum += die_roll

        message += f'For a total of **{pip_sum}.**'

        await ctx.send(message[0:2000])


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Game(bot))
