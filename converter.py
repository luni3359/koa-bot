"""Measurement finder by Moonatic (ThatsNoMoon#0175 on Discord)"""
import re
from itertools import dropwhile

from pint import UnitRegistry

from patterns import NUMBER_PATTERN, UNIT_PATTERN_TUPLE, SPECIAL_UNIT_PATTERN_TUPLE

ureg = UnitRegistry()
ureg.default_format = '~P.3f'
Q_ = ureg.Quantity


def find_units(s):
    """Get units from a string"""
    results = []
    i = 0
    while i < len(s):
        special_case_match = SPECIAL_UNIT_PATTERN_TUPLE[1].match(s, i)
        if special_case_match:
            results.append((SPECIAL_UNIT_PATTERN_TUPLE[0], float(special_case_match.group(1)), float(special_case_match.group(2))))
            i = special_case_match.end()
        else:
            num_match = NUMBER_PATTERN.match(s, i)
            if num_match:
                i = num_match.end()
                match = lambda u: (u[0], u[1].match(s, i))
                falsey = lambda x: not x[1]
                unit = next(dropwhile(falsey, map(match, iter(UNIT_PATTERN_TUPLE))), None)
                if unit:
                    (unit, unit_match) = unit
                    results.append((unit, float(num_match.group(1))))
                    i = unit_match.end()
            else:
                i += 1

    return results
