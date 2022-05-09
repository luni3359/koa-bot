
from dataclasses import dataclass
from typing import Any


@dataclass
class MultistreamUser():
    user_id: int
    name: str
    online: bool
    adult: bool


@dataclass
class PicartoChatSettings():
    guest_chat: bool
    links: bool
    level: bool


@dataclass
class PicartoLanguage():
    id: int
    name: str


@dataclass
class PicartoThumbnails():
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
    thumbnails: PicartoThumbnails
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
    chat_settings: PicartoChatSettings
    last_live: str
    tags: list[str]
    multistream: list[MultistreamUser]
    languages: list[PicartoLanguage]
    following: bool
