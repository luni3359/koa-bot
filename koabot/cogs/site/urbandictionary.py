from dataclasses import dataclass


@dataclass
class UrbanDefinition():
    definition: str
    permalink: str
    thumbs_up: int
    sound_urls: list[str]
    author: str
    word: str
    defid: str
    current_vote: str
    written_on: str
    example: str
    thumbs_down: int


@dataclass
class UrbanDefineTerm():
    list: list[UrbanDefinition]
