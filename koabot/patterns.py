"""Regex pattern constants"""
import re

URL_PATTERN = re.compile(r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-;?-_=@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)')

NUMBER_PATTERN = re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)')

UNIT_PATTERN_TUPLE = [
    ('foot', re.compile(r' *(\'|foot|feet|ft)(?!\w)')),
    ('inch', re.compile(r' *("|inch|inches|ins?)(?!\w)')),
    ('mile', re.compile(r' *(miles?|mi)(?!\w)')),
    ('pound', re.compile(r' *(pounds?|lbs?)(?!\w)')),
    ('meter', re.compile(r' *(meters?|metres?|mt?r?s?)(?!\w)')),
    ('centimeter', re.compile(r' *(centimeters?|centimetres?|cms?)(?!\w)')),
    ('kilometer', re.compile(r' *(kilometers?|kilometres?|kms?)(?!\w)')),
    ('kilogram', re.compile(r' *(kilograms?|kgs?)(?!\w)')),
    ('celsius', re.compile(r' *(°|degrees?|degs?)? *([Cc]|[CcSs]el[sc]ius)(?!\w)')),
    ('fahrenheit', re.compile(r' *(°|degrees?|degs?)? *([Ff]|[Ff]h?ah?rh?enheit)(?!\w)')),
    ('kelvin', re.compile(r' *(°|degrees?|degs?)? *([Kk]|[Kk]el[vb]in)(?!\w)')),
]

SPECIAL_UNIT_PATTERN_TUPLE = ('footinches', re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)\'(\.\d+|\d[,\d]*(?:\.\d+)?)"?'))

DICE_PATTERN = r'(\d*)d(\d+)(?:\ ?([+-]\d+))?'
