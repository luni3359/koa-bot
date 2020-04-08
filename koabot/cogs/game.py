import random
import re

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
            await ctx.send('Sorry, I can\'t do that...')
            return

        dice_single_or_many = len(dice_matches) > 1 or (dice_matches[0][0] and int(dice_matches[0][0]) > 1)
        message = '>>> {} rolled the {}.\n'.format(ctx.author.mention, dice_single_or_many and 'dice' or 'die')
        pip_sum = 0

        for match in dice_matches:
            quantity = match[0] and int(match[0]) or 1
            pips = match[1] and int(match[1]) or 1
            bonus_points = match[2] and int(match[2]) or 0

            message += '{} {}-sided {} for a '.format(num2words(quantity).capitalize(), pips, quantity > 1 and 'dice' or 'die')

            for i in range(0, quantity):
                die_roll = random.randint(1, pips)

                if i == quantity - 1:
                    if quantity == 1:
                        message += '{}.'.format(die_roll)
                    else:
                        message += 'and a {}.'.format(die_roll)

                    if bonus_points:
                        pip_sum += bonus_points

                        if bonus_points > 0:
                            message += ' +{}'.format(bonus_points)
                        else:
                            message += ' {}'.format(bonus_points)

                    message += '\n'
                elif i == quantity - 2:
                    message += '{} '.format(die_roll)
                else:
                    message += '{}, '.format(die_roll)

                pip_sum += die_roll

        message += 'For a total of **{}.**'.format(pip_sum)

        await ctx.send(message)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Game(bot))
