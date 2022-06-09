"""Unit manager for any dimension and type"""
import itertools

from discord.ext import commands
from forex_python import converter as forex_api
from pint import UnitRegistry

from koabot.kbot import KBot
from koabot.patterns import (NUMBER_PATTERN, SPECIAL_UNIT_PATTERN_TUPLE,
                             UNIT_PATTERN_TUPLE)


class Converter(commands.Cog):
    """Converter class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.ureg = UnitRegistry()
        self.ureg.default_format = "~P.3f"
        self.quantity = self.ureg.Quantity
        self.rates = forex_api.CurrencyRates()

    @commands.hybrid_command(name='convert', aliases=['conv', 'cv'])
    async def unit_convert(self, ctx: commands.Context, *, units: str = ""):
        """Convert units"""

        unit_matches = []
        i = 0
        while i < len(units):
            ftin_match = SPECIAL_UNIT_PATTERN_TUPLE[1].match(units, i)
            if ftin_match:
                unit_matches.append((SPECIAL_UNIT_PATTERN_TUPLE[0], float(
                    ftin_match.group(1)), float(ftin_match.group(2))))
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
            await self.convert_units(ctx, unit_matches)

    @commands.hybrid_command(name='exchange', aliases=['currency', 'xc'])
    async def convert_currency(self, ctx: commands.Context, amount: float, src_code: str, _, dst_code: str):
        """Convert an amount from one currency to another"""
        src_code = src_code.upper()
        dst_code = dst_code.upper()
        src_sym, dst_sym = map(forex_api.get_symbol, [src_code, dst_code])
        try:
            converted_amount = self.rates.convert(src_code, dst_code, amount)
            output = f"```{src_sym}{amount} {src_code} → {dst_sym}{converted_amount:0.2f} {dst_code}```"
        except forex_api.RatesNotAvailableError as e:
            output = f"There was a problem retrieving this data:\n{e}"
        await ctx.reply(output, mention_author=False)

    async def convert_units(self, ctx: commands.Context, units: list):
        """Convert units found to their opposite (SI <-> imp)
        Arguments:
            units::list
                List of units of measurement that have been parsed by unit_convert
        """
        conversion_str = '```'

        for unit_str, value, *extra_value in units:
            if unit_str == 'footinches':
                extra_value = extra_value[0]
                converted_value = (value * self.ureg.foot + extra_value * self.ureg.inch).to_base_units()
                calculation_str = f'{value * self.ureg.foot} {extra_value * self.ureg.inch} → {converted_value}'

                print(calculation_str)
                conversion_str += f'\n{calculation_str}'
                continue

            unit = self.ureg[unit_str]
            value = self.quantity(value, unit)

            if unit.u in dir(self.ureg.sys.imperial) or unit in (self.ureg['fahrenheit'], self.ureg['gallon']):
                if str(unit.dimensionality) == '[temperature]':
                    converted_value = value.to(self.ureg.celsius)
                else:
                    converted_value = value.to_base_units()
                    converted_value = converted_value.to_compact()
            # elif unit.u in dir(self.ureg.sys.mks):
            elif str(unit.dimensionality) == '[length]':
                if unit == self.ureg['kilometer']:
                    converted_value = value.to(self.ureg.miles)
                elif value.magnitude >= 300:
                    converted_value = value.to(self.ureg.yards)
                else:
                    raw_feet = value.to(self.ureg.feet)
                    inches = value.to(self.ureg.inch)
                    feet = int(inches.magnitude / 12)
                    remainder_inches = round(inches.magnitude % 12)
                    converted_value = f'{feet} ft {remainder_inches} in ({raw_feet})'

            elif str(unit.dimensionality) == '[length] ** 3':
                converted_value = value.to(self.ureg.gallon)

            elif str(unit.dimensionality) == '[mass]':
                converted_value = value.to(self.ureg.pounds)

            elif str(unit.dimensionality) == '[temperature]':
                converted_value = value.to(self.ureg.fahrenheit)

            calculation_str = f'{value} → {converted_value}'
            print(calculation_str)
            conversion_str += f'\n{calculation_str}'

        conversion_str += '```'
        await ctx.reply(conversion_str, mention_author=False)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Converter(bot))
