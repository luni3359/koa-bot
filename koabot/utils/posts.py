"""Post utilities"""
import re
from typing import Union

from koabot import koakuma


def get_post_id(url: str, words_to_match: Union[str, list], trim_to: str, /, *, has_regex: bool = False) -> int:
    """Get post id from url
    Arguments:
        url::str
            Url to extract the id from
        words_to_match::str or list
            First part to start looking from
        trim_to::str or regex pattern (str)
            The final part to stop at

    Keywords:
        has_regex::bool
            Indicates whether or not 'trim_to' should be treated
            as a regex pattern.
    """

    if not isinstance(words_to_match, list):
        words_to_match = [words_to_match]

    matching_word = False
    for v in words_to_match:
        if v in url:
            matching_word = v

    if not matching_word:
        return

    if has_regex:
        return re.findall(trim_to, url.split(matching_word)[1])[0]

    return url.split(matching_word)[1].split(trim_to)[0]


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
        return koakuma.list_contains(post['tags']['general'], koakuma.bot.rules['no_preview_tags'][board]) and post['rating'] != 's'
    if board == 'sankaku':
        return True

    return koakuma.list_contains(post['tag_string_general'].split(), koakuma.bot.rules['no_preview_tags'][board]) or post['is_banned']
