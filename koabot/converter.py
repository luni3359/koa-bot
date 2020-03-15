"""Unit manager"""
import random

from pint import UnitRegistry

import koabot

ureg = UnitRegistry()
ureg.default_format = '~P.3f'
Q_ = ureg.Quantity


async def convert_units(ctx, units):
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

    conversion_str = random.choice(koabot.koakuma.bot.quotes['converting_units']) + '```'

    for quantity in units:
        if quantity[0] == 'footinches':
            value = quantity[1]
            value2 = quantity[2]

            converted_value = value * ureg.foot + value2 * ureg.inch
            conversion_str += '\n%s %s → %s' % (value * ureg.foot, value2 * ureg.inch, converted_value.to_base_units())
            continue

        (unit, value) = quantity
        value = value * ureg[unit]

        if unit in imperial_units:
            converted_value = value.to_base_units()
            converted_value = converted_value.to_compact()
        elif unit in si_units:
            if unit == 'kilometers':
                converted_value = value.to(ureg.miles)
            elif unit == 'kilograms':
                converted_value = value.to(ureg.pounds)
            elif value.magnitude >= 300:
                converted_value = value.to(ureg.yards)
            else:
                converted_value = value.to(ureg.feet)

        conversion_str += '\n%s → %s' % (value, converted_value)

    conversion_str += '```'
    await ctx.send(conversion_str)
