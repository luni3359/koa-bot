"""Regex pattern constants"""
import re

URL_PATTERN = re.compile(r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-;?-_=@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)')

NUMBER_PATTERN = re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)')

UNIT_PATTERN_TUPLE = [
    # [length]
    ('inch', re.compile(r' *("|inch|inches|ins?)(?!\w)')),
    ('foot', re.compile(r' *(\'|foot|feet|ft)(?!\w)')),
    ('mile', re.compile(r' *(miles?|mi)(?!\w)')),
    ('yard', re.compile(r' *(yards?|yr?d)(?!\w)')),
    ('centimeter', re.compile(r' *(centimeters?|centimetres?|cms?)(?!\w)')),
    ('meter', re.compile(r' *(meters?|metres?|mt?r?s?)(?!\w)')),
    ('kilometer', re.compile(r' *(kilometers?|kilometres?|kms?)(?!\w)')),
    # [length ** 3]
    ('gallon', re.compile(r' *(gallons?|gal)(?!\w)')),
    ('liter', re.compile(r' *(liters?|litres?|lt?r?s?)(?!\w)')),
    # [mass]
    ('ounce', re.compile(r' *(ounces?|oz)(?!\w)')),
    ('pound', re.compile(r' *(pounds?|lbs?)(?!\w)')),
    ('gram', re.compile(r' *(grams?|gr?m?s?)(?!\w)')),
    ('kilogram', re.compile(r' *(kilograms?|kgs?)(?!\w)')),
    # [temperature]
    ('celsius', re.compile(r' *(°|degrees?|degs?)? *([Cc]|[CcSs]el[sc]ius)(?!\w)')),
    ('fahrenheit', re.compile(r' *(°|degrees?|degs?)? *([Ff]|[Ff]h?ah?rh?enheit)(?!\w)')),
    ('kelvin', re.compile(r' *(°|degrees?|degs?)? *([Kk]|[Kk]el[vb]in)(?!\w)')),
    ('rankine', re.compile(r' *(°|degrees?|degs?)? *([Rr]|[Rr]ankine?)(?!\w)')),
]

SPECIAL_UNIT_PATTERN_TUPLE = ('footinches', re.compile(r'(\.\d+|\d[,\d]*(?:\.\d+)?)\'(\.\d+|\d[,\d]*(?:\.\d+)?)"?'))

DICE_PATTERN = re.compile(r'(?:([+-])\ ?)?(?:(\d*)?d(\d+)(?:\ ?(k[hl]\d+))?|(\d+))')

CHANNEL_URL_PATTERN = re.compile(r'https:\/\/(?:ptb\.)?discord(?:app)?\.com\/channels(?:\/\d{18,19}){3}')

DISCORD_EMOJI_PATTERN = re.compile(r'(<:[\w_]{1,32}:\d{18}>)')

HTML_BR_TAG = re.compile(r'<br *\/>')

HTML_TAG_OR_ENTITY_PATTERN = re.compile(r'<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

COMMAND_PATTERN = re.compile(r'^!([a-zA-Z0-9]+)')

LINEBREAK_PATTERN = re.compile(r'\n')
