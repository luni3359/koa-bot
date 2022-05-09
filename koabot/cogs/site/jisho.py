from dataclasses import dataclass


@dataclass
class JapaneseWord():
    word: str
    reading: str


@dataclass
class JishoLink():
    text: str
    url: str


@dataclass
class JishoSense():
    english_definitions: list[str]
    parts_of_speech: list[str]
    links: list[JishoLink]
    tags: list
    restrictions: list
    see_also: list
    antonyms: list
    source: list
    info: list


@dataclass
class JishoDefinition():
    slug: str
    is_common: bool
    tags: list[str]
    jlpt: list[str]
    japanese: list[JapaneseWord]
    senses: list[JishoSense]
    attribution: dict


@dataclass
class JishoResponse():
    meta: dict
    data: list[JishoDefinition]
