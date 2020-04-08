"""Unit manager for any dimension and type"""
import itertools
import random

import forex_python.converter as currency
from discord.ext import commands
from pint import UnitRegistry

from koabot.patterns import (NUMBER_PATTERN, SPECIAL_UNIT_PATTERN_TUPLE,
                             UNIT_PATTERN_TUPLE)


class Converter(commands.Cog):
    """Converter class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ureg = UnitRegistry()
        self.ureg.default_format = '~P.3f'
        self.Q_ = self.ureg.Quantity
        self.currency = currency.CurrencyRates()

    @commands.command(name='convert', aliases=['conv', 'cv'])
    async def unit_convert(self, ctx, *, units):
        """Convert units"""

        unit_matches = []
        i = 0
        while i < len(units):
            ftin_match = SPECIAL_UNIT_PATTERN_TUPLE[1].match(units, i)
            if ftin_match:
                unit_matches.append((SPECIAL_UNIT_PATTERN_TUPLE[0], float(ftin_match.group(1)), float(ftin_match.group(2))))
                # unit_matches.append((unit_name, value in feet, value in inches))
                i = ftin_match.end()
                continue

            num_match = NUMBER_PATTERN.match(units, i)
            if num_match:
                i = num_match.end()
                def match(u): return (u[0], u[1].match(units, i))
                def falsey(x): return not x[1]
                unit = next(itertools.dropwhile(falsey, map(match, iter(UNIT_PATTERN_TUPLE))), None)
                if unit:
                    (unit, unit_match) = unit
                    unit_matches.append((unit, float(num_match.group(1))))
                    i = unit_match.end()

            i += 1

        if unit_matches:
            await self.bot.converter.convert_units(ctx, unit_matches)

    @commands.command(name='exchange', aliases=['currency', 'xc', 'c'])
    async def convert_currency(self, ctx, amount: float, currency_type1: str, _, currency_type2: str):
        """Convert currency to others"""

        currency_type1 = currency_type1.upper()
        currency_type2 = currency_type2.upper()
        converted_amount = self.currency.convert(currency_type1, currency_type2, amount)

        await ctx.send('```%s %s → %0.2f %s```' % (amount, currency_type1, converted_amount, currency_type2))

    async def convert_units(self, ctx, units):
        """Convert units found to their opposite (SI <-> imp)"""

        imperial_units = [
            'feet',
            'inches',
            'miles',
            'pounds',
        ]
        si_units = [
            'meters',
            'centimeters',
            'kilometers',
            'kilograms'
        ]

        if not units:
            return

        conversion_str = random.choice(self.bot.quotes['converting_units']) + '```'

        for quantity in units:
            if quantity[0] == 'footinches':
                value = quantity[1]
                value2 = quantity[2]

                converted_value = (value * self.ureg.foot + value2 * self.ureg.inch).to_base_units()
                print('%s %s → %s' % (value * self.ureg.foot, value2 * self.ureg.inch, converted_value))
                conversion_str += '\n%s %s → %s' % (value * self.ureg.foot, value2 * self.ureg.inch, converted_value)
                continue

            (unit, value) = quantity
            value = value * self.ureg[unit]

            if unit in imperial_units:
                converted_value = value.to_base_units()
                converted_value = converted_value.to_compact()
            elif unit in si_units:
                if unit == 'kilometers':
                    converted_value = value.to(self.ureg.miles)
                elif unit == 'kilograms':
                    converted_value = value.to(self.ureg.pounds)
                elif value.magnitude >= 300:
                    converted_value = value.to(self.ureg.yards)
                else:
                    converted_value = value.to(self.ureg.feet)

            print('%s → %s' % (value, converted_value))
            conversion_str += '\n%s → %s' % (value, converted_value)

        conversion_str += '```'
        await ctx.send(conversion_str)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(Converter(bot))
