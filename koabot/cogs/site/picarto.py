
from dataclasses import dataclass
from typing import Any


@dataclass
class MultistreamUser():
    user_id: int
    name: str
    online: bool
    adult: bool


@dataclass
class ChatSettings():
    guest_chat: bool
    links: bool
    level: bool


@dataclass
class Language():
    id: int
    name: str


@dataclass
class Thumbnails():
    web: str
    web_large: str
    mobile: str
    tablet: str


@dataclass
class PicartoChannel():
    user_id: int
    name: str
    avatar: str
    online: bool
    viewers: int
    viewers_total: int
    thumbnails: Thumbnails
    followers: int
    subscribers: int
    adult: bool
    category: list[str]
    account_type: str
    commissions: bool
    recordings: bool
    title: str
    description_panels: list[dict]
    private: bool
    private_message: Any
    gaming: bool
    chat_settings: ChatSettings
    last_live: str
    tags: list[str]
    multistream: list[MultistreamUser]
    languages: list[Language]
    following: bool
