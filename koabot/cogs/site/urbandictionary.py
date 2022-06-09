import re
import urllib
from dataclasses import dataclass

import discord
from dataclass_wizard import fromdict
from discord.ext import commands

import koabot.core.net as net_core
from koabot.cogs.infolookup import Dictionary
from koabot.kbot import KBot


@dataclass
class Definition():
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
class UrbanResponse():
    list: list[Definition]


class SiteUrbanDictionary(Dictionary):
    """UrbanDictionary operations handler"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self.guide: dict = self.bot.assets['urban_dictionary']
        self.max_definition_length = 2048

    def strip_markup(self, text: str):
        """Trim weird markup from results"""
        text = text.replace('*', '\\*')

        matches = re.findall(r'(\[([\w\ ’\']+)\])', text, re.IGNORECASE)
        for match in matches:
            text = text.replace(
                match[0], f"[{match[1]}]({self.bot.assets['urban_dictionary']['dictionary_url']}{urllib.parse.quote(match[1])})")

        return text

    async def search(self, ctx: commands.Context, search_term: str):
        search_term = search_term.lower()
        search_encoded = urllib.parse.quote_plus(search_term)
        user_search = self.guide['search_url'] + search_encoded

        if not (js := (await net_core.http_request(user_search, json=True)).json):
            await ctx.send('Error retrieving data from server.')
            return

        js = fromdict(UrbanResponse, js)

        # Check if there are any results at all
        if not hasattr(js, 'list') or not js.list:
            return await ctx.send(self.botstatus.get_quote('dictionary_no_results'))

        definition_embeds: list[discord.Embed] = []
        embed = discord.Embed()
        embed.title = search_term
        embed.url = self.guide['dictionary_url'] + search_encoded
        embed.description = ''
        definition_embeds.append(embed)
        index_placeholder = '<<INDEX>>'

        for i, entry in enumerate(js.list[:3]):
            definition = entry.definition
            example = entry.example

            string_to_add = f"**{index_placeholder}. {self.strip_markup(definition)}**\n\n"
            string_to_add += self.strip_markup(example) + '\n\n'

            if len(string_to_add) - len(index_placeholder) + 1 > self.max_definition_length:
                string_to_add = string_to_add[:self.max_definition_length]
                await ctx.send('What a massive definition...')

            if i > 0 and len(embed.description) + len(string_to_add) - len(index_placeholder) + 1 > self.max_definition_length:
                definition_embeds.append(discord.Embed(description=string_to_add))
            else:
                embed.description += string_to_add

        definition_embeds[-1].set_footer(text=self.guide['name'], icon_url=self.guide['favicon']['size16'])

        i = 0
        for embed in definition_embeds:
            previous_desc = ''
            while True:
                i += 1
                previous_desc = embed.description
                embed.description = embed.description.replace(index_placeholder, str(i), 1)
                if len(previous_desc) == len(embed.description):
                    i -= 1
                    break
            await ctx.send(embed=embed)


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(SiteUrbanDictionary(bot))
