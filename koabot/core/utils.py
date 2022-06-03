import hashlib
import os
from pathlib import Path


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
