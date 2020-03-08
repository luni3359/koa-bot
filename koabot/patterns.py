"""Regex pattern constants"""
import re

URL_PATTERN = re.compile(r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-;?-_=@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)')

NUMBER_PATTERN = re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)')
UNIT_PATTERN_TUPLE = [
    ('feet', re.compile(r' *(\'|foot|feet|ft)(?!\w)')),
    ('inches', re.compile(r' *("|inch|inches|ins?)(?!\w)')),
    ('miles', re.compile(r' *(miles?|mi)(?!\w)')),
    ('pounds', re.compile(r' *(pounds?|lbs?)(?!\w)')),
    ('meters', re.compile(r' *(meters?|metres?|mt?r?s?)(?!\w)')),
    ('centimeters', re.compile(r' *(centimeters?|centimetres?|cms?)(?!\w)')),
    ('kilometers', re.compile(r' *(kilometers?|kilometres?|kms?)(?!\w)')),
    ('kilograms', re.compile(r' *(kilograms?|kgs?)(?!\w)')),
]
SPECIAL_UNIT_PATTERN_TUPLE = ('footinches', re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)\'(\.\d+|\d[,\d]*(?:\.\d+)?)"?'))

DICE_PATTERN = r'(\d*)d(\d+)(?:\ ?([+-]\d+))?'
