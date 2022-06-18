"""Search information and definitions"""
import math
import re
import urllib

import discord
from discord.ext import commands

import koabot.core.net as net_core
from koabot.cogs.botstatus import BotStatus
from koabot.core.site import Site
from koabot.kbot import KBot


class Dictionary(Site):
    """Class that all dictionary sites inherit from"""

    def __init__(self, bot: KBot) -> None:
        super().__init__(bot)
        self._merriam_find_pattern = None

    @property
    def merriam_find_pattern(self) -> re.Pattern:
        if not self._merriam_find_pattern:
            self._merriam_find_pattern = re.compile(
                r'({[a-z_]+[\|}]+([a-zÀ-Ž\ \-\,]+)(?:{\/[a-z_]*|[a-z0-9\ \-\|\:\(\)]*)})', re.IGNORECASE)
        return self._merriam_find_pattern

    def strip_markup(self, txt: str, service: str):
        """Trim weird markup from dictionary entries"""
        match service:
            case 'merriam':
                # Properly format words encased in weird characters

                # Remove all filler
                txt = re.sub(r'\{bc\}|\*', '', txt)

                while (matches := self.merriam_find_pattern.findall(txt)):
                    for match in matches:
                        txt = txt.replace(match[0], f"*{match[1].upper()}*")

                txt = re.sub(r'\{\/?[a-z\ _\-]+\}', '', txt)
                print(txt)
                return txt

    async def search(self, ctx: commands.Context, query: str) -> str:
        raise NotImplementedError


class InfoLookup(commands.Cog):
    """InfoLookup class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

        self._merriam_find_pattern: re.Pattern = None

    @property
    def dictionary_cog(self) -> Dictionary:
        return self.bot.get_cog('Dictionary')

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @commands.hybrid_command(name='wikipedia', aliases=['wk', 'wp'])
    async def search_wikipedia(self, ctx: commands.Context, *, search_term: str):
        """Search for articles in Wikipedia"""
        wikipedia_cog: Dictionary = self.bot.get_cog("SiteWikipedia")
        await wikipedia_cog.search(ctx, search_term)

    @commands.hybrid_command(name='jisho', aliases=['j'])
    async def search_jisho(self, ctx: commands.Context, *, search_term: str):
        """Search a term in the japanese dictionary jisho"""
        jisho_cog: Dictionary = self.bot.get_cog("SiteJisho")
        await jisho_cog.search(ctx, search_term)

    @commands.hybrid_command(name='urbandictionary', aliases=['wu', 'udictionary', 'ud'])
    async def search_urbandictionary(self, ctx: commands.Context, *, search_term: str):
        """Search a term in urbandictionary"""
        urban_cog: Dictionary = self.bot.get_cog("SiteUrbanDictionary")
        await urban_cog.search(ctx, search_term)

    @commands.hybrid_command(name='dictionary', aliases=['d', 'word', 'w'])
    async def search_english_word(self, ctx: commands.Context, *, search_term: str):
        """Search a term in merriam-webster's dictionary"""
        MAX_DEFINITION_LENGTH = 2048
        guide = self.bot.assets['merriam-webster']
        search_term = search_term.lower()
        search_encoded = urllib.parse.quote(search_term)
        user_search = f"{guide['search_url']}/{search_encoded}?key={self.bot.auth_keys['merriam-webster']['key']}"

        # Check if there are any results at all
        if not (js := (await net_core.http_request(user_search, json=True)).json):
            return await ctx.send(self.botstatus.get_quote('dictionary_no_results'))

        # If word has no direct definitions, they're word suggestions
        # (if there's no dicts, it's safe to assume they're strings)
        if not isinstance(js[0], dict):
            suggestion_list = '\n\n'.join([f"• {suggestion}" for suggestion in js[:5]])

            embed = discord.Embed()
            embed.description = f"*{suggestion_list}*"
            embed.set_footer(text=guide['name'], icon_url=guide['favicon'])
            return await ctx.send(self.botstatus.get_quote('dictionary_try_this'), embed=embed)
        # If there's suggestions to a different grammatical tense
        elif 'def' not in js[0]:
            tense_group = js[0]['cxs'][0]
            tense_name = tense_group['cxl'].replace(' of', '')
            suggested_tense_word = tense_group['cxtis'][0]['cxt']
            await ctx.send(f"The word **\"{search_term}\"** is the *{tense_name}* of the verb **\"{suggested_tense_word}\"**. Here's its definition.")
            await ctx.invoke(self.bot.get_command('dictionary'), suggested_tense_word)
            return

        dictionary_cog: Dictionary = self.dictionary_cog
        embed = discord.Embed()
        embed.title = search_term
        embed.url = f"{guide['dictionary_url']}/{search_encoded}"
        embed.description = ""

        for category in js[:2]:
            if not 'def' in category or not 'hwi' in category:
                continue

            pronunciation = category['hwi']['hw']
            definitions = category['def']

            embed.description += f"►  *{pronunciation.replace('*', '・')}*"

            if 'fl' in category:
                embed.description += f"\n\n__**{category['fl'].upper()}**__"

            for subcategory in definitions:
                similar_meaning_string = ""
                for similar_meanings in subcategory['sseq']:
                    for meaning in similar_meanings:
                        meaning_item = meaning[1]

                        if isinstance(meaning_item, list):
                            meaning_item = meaning_item[0]

                        if isinstance(meaning_item, dict):
                            meaning_position = meaning_item.get('sn', "1")
                        else:
                            meaning_position = "1"

                        if not meaning_position[0].isdigit():
                            meaning_position = '\u3000' + meaning_position

                        # Get definition
                        # What a mess
                        if isinstance(meaning_item, list):
                            if 'sense' in meaning_item[1]:
                                definition = meaning_item[1]['sense']['dt'][0][1]
                            else:
                                definition = meaning_item[1]['dt'][0][1]
                        elif 'dt' in meaning_item:
                            definition = meaning_item['dt'][0][1]
                        elif 'sense' in meaning_item:
                            definition = meaning_item['sense']['dt'][0][1]
                        elif 'sls' in meaning_item:
                            definition = ', '.join(meaning_item['sls'])
                        elif 'lbs' in meaning_item:
                            definition = meaning_item['lbs'][0]
                        elif 'ins' in meaning_item:
                            if 'spl' in meaning_item['ins'][0]:
                                definition = meaning_item['ins'][0]['spl'].upper() + ' ' + meaning_item['ins'][0]['if']
                            else:
                                definition = meaning_item['ins'][0]['il'] + ' ' + meaning_item['ins'][0]['if'].upper()
                        else:
                            raise KeyError('Dictionary format could not be resolved.')

                        if isinstance(definition, list):
                            definition = definition[0][0][1]

                        # Format bullet point
                        similar_meaning_string += f'{meaning_position}: {definition}\n'

                subcategory_text = subcategory.get('vd', "definition")
                embed.description += f"\n**{subcategory_text}**\n{dictionary_cog.strip_markup(similar_meaning_string, 'merriam')}"

            # Add etymology
            if 'et' in category:
                etymology = category['et']
                embed.description += f"\n**etymology**\n{dictionary_cog.strip_markup(etymology[0][1], 'merriam')}\n\n"
            else:
                embed.description += "\n\n"

        # Embed descriptions longer than 4096 characters error out.
        if len(embed.description) > MAX_DEFINITION_LENGTH:
            print(f"Definition over {MAX_DEFINITION_LENGTH} characters")
            embeds_to_send = math.ceil(len(embed.description) / MAX_DEFINITION_LENGTH) - 1
            embeds_sent = 0

            dictionary_definitions = embed.description
            embed.description = dictionary_definitions[:MAX_DEFINITION_LENGTH]

            await ctx.send(embed=embed)

            # Print all the message across many embeds
            while embeds_sent < embeds_to_send:
                embeds_sent += 1

                embed = discord.Embed()
                embed.description = dictionary_definitions[MAX_DEFINITION_LENGTH *
                                                           embeds_sent:MAX_DEFINITION_LENGTH * (embeds_sent + 1)]

                if embeds_sent == embeds_to_send:
                    embed.set_footer(text=guide['name'], icon_url=guide['favicon'])

                await ctx.send(embed=embed)
        else:
            embed.set_footer(text=guide['name'], icon_url=guide['favicon'])
            await ctx.send(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(self.botstatus.get_quote('dictionary_blank_search'))


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Dictionary(bot))
    await bot.add_cog(InfoLookup(bot))
