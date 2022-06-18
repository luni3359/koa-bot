import re
import urllib
from dataclasses import dataclass

import discord
from dataclass_wizard import fromdict
from discord.ext import commands

import koabot.core.net as net_core
from koabot.cogs.infolookup import Dictionary
from koabot.core import utils
from koabot.kbot import KBot


@dataclass
class JapaneseWord():
    word: str | None = None
    reading: str | None = None


@dataclass
class Link():
    text: str
    url: str


@dataclass
class Sense():
    english_definitions: list[str]
    parts_of_speech: list[str]
    links: list[Link]
    tags: list[str]
    restrictions: list
    see_also: list[str]
    antonyms: list[str]
    source: list
    info: list[str]


@dataclass
class Definition():
    slug: str
    tags: list[str]
    jlpt: list[str]
    japanese: list[JapaneseWord]
    senses: list[Sense]
    attribution: dict[str, bool]
    is_common: bool | None = None


@dataclass
class JishoResponse():
    meta: dict
    data: list[Definition]


class SiteJisho(Dictionary):
    """Jisho operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.max_definition_length = 2048

    async def search(self, ctx: commands.Context, search_term: str):
        guide = self.bot.assets['jisho']
        search_term = search_term.lower()
        word_encoded = urllib.parse.quote_plus(search_term)
        user_search = guide['search_url'] + word_encoded

        if not (js := (await net_core.http_request(user_search, json=True)).json):
            await ctx.send('Error retrieving data from server.')
            return

        js = fromdict(JishoResponse, js)

        # Check if there are any results at all
        if js.meta['status'] != 200:
            return await ctx.send(self.botstatus.get_quote('dictionary_no_results'))

        embed = discord.Embed()
        embed.title = search_term
        embed.url = guide['dictionary_url'] + urllib.parse.quote(search_term)
        dictionary_definitions: str = ""

        for word in js.data[:4]:
            japanese_info = word.japanese[0]
            senses_info = word.senses[0]

            kanji = japanese_info.word if japanese_info.word else japanese_info.reading
            # jlpt_level = ', '.join(word['jlpt'])
            en_definitions = '; '.join(senses_info.english_definitions)
            what_it_is = '; '.join(senses_info.parts_of_speech)

            dictionary_definitions += f'**{kanji}**'

            # The primary kana reading for this word
            if (primary_reading := japanese_info.reading if japanese_info.reading else None) and primary_reading != kanji:
                dictionary_definitions += f' ({primary_reading})'

            # The tags attached to the word i.e. Computing, Medicine, Biology
            if (tags := '; '.join(senses_info.tags)):
                dictionary_definitions += f'\n*{tags}*'

            dictionary_definitions += f'\n{what_it_is}'

            # if jlpt_level:
            #     jlpt_level = jlpt_level.replace('jlpt-n', 'N')
            #     definition += f' [{jlpt_level}]'

            dictionary_definitions += f':\n{en_definitions}'

            if senses_info.info and (definition_clarification := ', '.join(senses_info.info)):
                dictionary_definitions += f'\n*{definition_clarification}*'

            dictionary_definitions += '\n\n'

        embed.color = 0x56d926
        embed.description = utils.smart_truncate(dictionary_definitions, self.max_definition_length)
        embed.set_footer(text=guide['name'], icon_url=guide['favicon']['size16'])

        await ctx.send(embed=embed)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteJisho(bot))
