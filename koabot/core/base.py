"""Helper functions"""


def list_contains(lst: list, items_to_be_matched: list) -> bool:
    """Helper function for checking if a list contains any elements of another list"""
    # https://stackoverflow.com/a/17735466/7688278
    return not set(lst).isdisjoint(items_to_be_matched)
