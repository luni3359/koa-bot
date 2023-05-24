"""Various functions that are unique enough to not go into their own cog"""
import hashlib
import html
import os
from pathlib import Path

import bs4

from koabot.patterns import (HTML_BR_TAG, HTML_TAG_OR_ENTITY_PATTERN,
                             LINEBREAK_PATTERN)


def list_contains(lst: list, items_to_be_matched: list) -> bool:
    """Helper function for checking if a list contains any elements of another list"""
    # https://stackoverflow.com/a/17735466/7688278
    return not set(lst).isdisjoint(items_to_be_matched)


def path_from_extension(extension: str) -> Path:
    """Retrieves the absolute path from an extension"""
    slashed_path = extension.replace(".", os.sep)
    return Path(f"{slashed_path}.py")


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


def trim_linebreaks(text: str, *, keep: int = 0) -> str:
    """Trims linebreaks from a string

    Arguments:
        text::str
            The text to trim linebreaks from
    Keywords
        keep::int
            The number of linebreaks to keep consecutively
            ie. with keep=1 only every second consecutive linebreak onwards will be removed
            (seems to be done by default on DA and pixiv...)
    """
    if keep is None:
        # Unable to tell how many to keep. Skipping process
        return text

    i = 0
    consecutive_count = 0
    while i < len(text):
        if (lb_match := LINEBREAK_PATTERN.match(text, i)):
            lb_match_end = lb_match.end()

            consecutive_count += 1
            if consecutive_count > keep:
                text = text[:i] + LINEBREAK_PATTERN.sub('', text[i:], 1)
                continue

            i = lb_match_end
            continue
        elif text[i] != ' ':
            consecutive_count = 0

        i += 1
    return text


def strip_html_markup(text: str, *, keep_br: int = None) -> str:
    """Strips off all HTML from the given string
    Arguments:
        text::str
            The string to strip from

    Keywords:
        keep_br::int (optional)
            The number of consecutive br tags to keep. They will remain as \n instead
            Doesn't try to remove br any tags by default
    """
    text = HTML_BR_TAG.sub('\n', text)  # Converts all br tags into \n
    text = trim_linebreaks(text, keep=keep_br)
    return HTML_TAG_OR_ENTITY_PATTERN.sub('', text)


def convert_code_points(text: str) -> str:
    """Converts code points, entities, or whatever the things that look like &#128521; 
    are called like into their respective characters (i.e. 😉). Transforms <a> tags into 
    markdown links

    Returns:
        str - Converted html markup (sadly. would be best with just the replacements)
    """
    # Turns all a tags into proper markdown urls
    parsed_html = bs4.BeautifulSoup(text, "lxml")
    for a in parsed_html.find_all("a", href=True):
        a: bs4.element.Tag
        a.replace_with(f"[{a.text}]({a['href']})")

    # unescape does the converting magic
    return str(html.unescape(parsed_html))
