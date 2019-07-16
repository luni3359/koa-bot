"""Measurement finder by Moonatic (ThatsNoMoon#0175 on Discord)"""
import re
from itertools import dropwhile

from pint import UnitRegistry

ureg = UnitRegistry()
ureg.default_format = '~P.3f'
Q_ = ureg.Quantity

num = re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)')
units = [
        ('feet', re.compile(r' *(\'|foot|feet|fts?)')),
        ('inches', re.compile(r' *("|inch|inches|ins?)')),
        ('miles', re.compile(r' *(miles?|mi)')),
        ('meters', re.compile(r' *(meters?|metres?|m)')),
        ('centimeters', re.compile(r' *(centimeters?|centimetres?|cm)')),
        ('kilometers', re.compile(r' *(kilometers?|kilometres?|km)')),
]
sad_foot_inches_special_case = ('footinches', re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)\'(\.\d+|\d[,\d]*(?:\.\d+)?)"?'))

def find_measurements(s):
    """Get unit of measure from a string"""
    results = []
    i = 0
    while i < len(s):
        sad_special_case_match = sad_foot_inches_special_case[1].match(s, i)
        if sad_special_case_match:
            results.append((sad_foot_inches_special_case[0], float(sad_special_case_match.group(1)), float(sad_special_case_match.group(2))))
            i += sad_special_case_match.end()
        else:
            num_match = num.match(s, i)
            if num_match:
                i += num_match.end()
                match = lambda u: (u[0], u[1].match(s, i))
                falsey = lambda x: not x[1]
                unit = next(dropwhile(falsey, map(match, iter(units))), None)
                if unit:
                    (unit, unit_match) = unit
                    results.append((unit, float(num_match.group(1))))
                    i += unit_match.end()
            else:
                i += 1

    return results
