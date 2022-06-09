"""Various functions that are unique enough to not go into their own cog"""
import hashlib
import os
from pathlib import Path

from koabot.patterns import HTML_TAG_OR_ENTITY_PATTERN


def list_contains(lst: list, items_to_be_matched: list) -> bool:
    """Helper function for checking if a list contains any elements of another list"""
    # https://stackoverflow.com/a/17735466/7688278
    return not set(lst).isdisjoint(items_to_be_matched)


def path_from_extension(extension: str) -> Path:
    """Retrieves the absolute path from an extension"""
    return Path(extension.replace('.', os.sep)+'.py')


def calculate_sha1(file: str | Path) -> str:
    """https://stackoverflow.com/a/22058673/7688278"""
    sha1_hash = hashlib.sha1()

    with open(file, 'rb') as f:
        while True:
            if not (data := f.read(65536)):  # lets read stuff in 64kb chunks! (arbitrary number)
                break
            sha1_hash.update(data)

    return sha1_hash.hexdigest()


def smart_truncate(text: str, length: int, inclusive: bool = False) -> str:
    """Truncates a string without harshly cutting off words"""
    # Max length is irrelevant
    if length > len(text):
        return text

    i = length
    if inclusive:
        l = len(text)
        while i < l and text[i] != ' ':
            i += 1
    else:
        while i > 0 and text[i] != ' ':
            i -= 1
    return text[:i]


def strip_html_markup(text: str) -> str:
    """Strips off all HTML from the given string"""
    return HTML_TAG_OR_ENTITY_PATTERN.sub('', text)
