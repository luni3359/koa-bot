"""Post utilities"""
import re
from typing import Union

from koabot import koakuma
from koabot.utils.base import list_contains


def get_name_or_id(url: str, /, *, start: Union[str, list] = [], end: Union[str, list] = ['?'], pattern: str = "") -> str:
    """Get a name or an id from an url
    Arguments:
        url::str
            Url to extract the id from
    Keywords:
        start::str | list
            First part to start looking from
        end::str | list
            The final part to stop at. By default it tries to trim out
            anything past a question mark.
        pattern::str (regex pattern)
            If set to a pattern, it will be used after <start> and <end>
            have done their job.
    """

    if not isinstance(start, list):
        start = [start]

    starting_match = None
    for v in start:
        if v in url:
            starting_match = v

    if not starting_match:
        return

    # Index 1, because index 0 is everything before the character that matched
    url = url.split(starting_match)[1]

    if not isinstance(end, list):
        end = [end]

    ending_match = None
    for v in end:
        if v in url:
            ending_match = v

    if ending_match:
        # Index 0, because index 1 is everything after the character that matched
        url = url.split(ending_match)[0]

    if pattern:
        return re.findall(pattern, url)[0]

    return url


def combine_tags(tags: Union[str, list], /,  *, maximum: int = 5) -> str:
    """Combine tags and give them a readable format
    Arguments:
        tags::str or list

    Keywords:
        maximum::int
            How many tags should be taken into account
    """
    if not isinstance(tags, list):
        tag_list = tags.split()
    else:
        tag_list = tags

    tag_count = len(tag_list)

    if tag_count > 1:
        tag_list = tag_list[:maximum]

        if tag_count > maximum:
            joint_tags = ', '.join(tag_list)
            joint_tags += f' and {tag_count - maximum} more'
        else:
            joint_tags = ', '.join(tag_list[:-1])
            joint_tags += ' and ' + tag_list[-1]

        return joint_tags.strip().replace('_', ' ')

    return ''.join(tag_list).strip().replace('_', ' ')


def post_is_missing_preview(post, /, *, board: str = 'danbooru') -> bool:
    """Determine whether or not a post is missing its preview
    Arguments:
        post::json object

    Keywords:
        board::str
            The board to check the rules with. Default is 'danbooru'
    """
    if board == 'e621':
        return list_contains(post['tags']['general'], koakuma.bot.rules['no_preview_tags'][board]) and post['rating'] != 's'
    if board == 'sankaku':
        return True

    return list_contains(post['tag_string_general'].split(), koakuma.bot.rules['no_preview_tags'][board]) or post['is_banned']
