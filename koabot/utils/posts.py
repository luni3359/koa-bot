"""Post utilities"""
import re
import typing


def get_post_id(url, words_to_match, trim_to, has_regex=False):
    """Get post id from url
    Arguments:
        url::str
        words_to_match::str or list
        trim_to::str or regex
        has_regex::bool
    """

    if not isinstance(words_to_match, typing.List):
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


def combine_tags(tags):
    """Combine tags and give them a readable format
    Arguments:
        tags::str or list
    """

    if isinstance(tags, typing.List):
        tag_list = tags
    else:
        tag_list = tags.split()[:5]

    if len(tag_list) > 1:
        joint_tags = ', '.join(tag_list[:-1])
        joint_tags += ' and ' + tag_list[-1]
        return joint_tags.strip().replace('_', ' ')

    return ''.join(tag_list).strip().replace('_', ' ')
