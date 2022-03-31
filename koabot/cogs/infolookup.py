"""Search information and definitions"""
import math
import re
import urllib

import discord
from discord.ext import commands
from mediawiki import MediaWiki
from mediawiki import exceptions as MediaExceptions

import koabot.core.net as net_core
from koabot.cogs.botstatus import BotStatus
from koabot.kbot import KBot


class InfoLookup(commands.Cog):
    """InfoLookup class"""

    def __init__(self, bot: KBot) -> None:
        self.bot = bot

        self._wikipedia: MediaWiki = None
        self._merriam_find_pattern: re.Pattern = None

    @property
    def botstatus(self) -> BotStatus:
        return self.bot.get_cog('BotStatus')

    @property
    def wikipedia(self) -> MediaWiki:
        if not self._wikipedia:
            self._wikipedia = MediaWiki()

        return self._wikipedia

    @property
    def merriam_find_pattern(self) -> re.Pattern:
        if not self._merriam_find_pattern:
            self._merriam_find_pattern = re.compile(
                r'({[a-z_]+[\|}]+([a-zÀ-Ž\ \-\,]+)(?:{\/[a-z_]*|[a-z0-9\ \-\|\:\(\)]*)})', re.IGNORECASE)

        return self._merriam_find_pattern

    def strip_dictionary_oddities(self, txt: str, service: str):
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
            case 'urban':
                txt = txt.replace('*', '\\*')

                matches = re.findall(r'(\[([\w\ ’\']+)\])', txt, re.IGNORECASE)
                for match in matches:
                    txt = txt.replace(
                        match[0], f"[{match[1]}]({self.bot.assets['urban_dictionary']['dictionary_url']}{urllib.parse.quote(match[1])})")

                return txt

    @commands.command(name='wikipedia', aliases=['wk', 'wp'])
    async def search_wikipedia(self, ctx: commands.Context, *, search_term: str):
        """Search for articles in Wikipedia"""
        MAX_SUMMARY_LENGTH = 2000
        guide = self.bot.guides['explanation']['wikipedia-default']

        page_results = self.wikipedia.search(search_term)
        page_title = []

        try:
            page_title = page_results[0]
        except IndexError:
            bot_msg = "I can't find anything relevant. Sorry..."
            await ctx.send(bot_msg)
            return

        # TODO: Check out that new wikimedia feature!
        try:
            page = self.wikipedia.page(page_title, auto_suggest=False)
            summary = page.summary
            embed = discord.Embed()
            embed.title = page.title
            embed.url = page.url
            if len(summary) > MAX_SUMMARY_LENGTH:
                summary = summary[:MAX_SUMMARY_LENGTH]
                for i in range(MAX_SUMMARY_LENGTH):
                    if summary[len(summary) - i - 1] != ' ':
                        continue

                    summary = summary[:len(summary) - i - 1] + '…'
                    break

            js = (await net_core.http_request(f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}", json=True)).json
            if 'thumbnail' in js:
                embed.set_image(url=js['thumbnail']['source'])

            embed.description = summary
            embed.set_footer(text=guide['embed']['footer_text'], icon_url=guide['embed']['favicon']['size16'])
            await ctx.send(embed=embed)
        except MediaExceptions.DisambiguationError as e:
            bot_msg = 'There are many definitions for that... do you see anything that matches?\n'

            for suggestion in e.options[:3]:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)
        except MediaExceptions.PageError:
            bot_msg = "Oh, I can't find anything like that... how about these?\n"
            suggestions = self.wikipedia.search(search_term, results=3)

            for suggestion in suggestions:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)

    @commands.command(name='jisho', aliases=['j'])
    async def search_jisho(self, ctx: commands.Context, *, search_term: str):
        """Search a term in the japanese dictionary jisho"""
        MAX_DEFINITION_LENGTH = 2048
        guide = self.bot.assets['jisho']
        search_term = search_term.lower()
        word_encoded = urllib.parse.quote_plus(search_term)
        user_search = guide['search_url'] + word_encoded

        if not (js := (await net_core.http_request(user_search, json=True)).json):
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if js['meta']['status'] != 200:
            return await ctx.send(self.botstatus.get_quote('dictionary_no_results'))

        embed = discord.Embed()
        embed.title = search_term
        embed.url = guide['dictionary_url'] + urllib.parse.quote(search_term)
        dictionary_definitions = ""

        for word in js['data'][:4]:
            japanese_info = word['japanese'][0]
            senses_info = word['senses'][0]

            kanji = japanese_info.get('word', japanese_info.get('reading'))
            # jlpt_level = ', '.join(word['jlpt'])
            en_definitions = '; '.join(senses_info['english_definitions'])
            what_it_is = '; '.join(senses_info['parts_of_speech'])

            dictionary_definitions += f'►{kanji}'

            # The primary kana reading for this word
            if (primary_reading := japanese_info.get('reading', None)) and primary_reading != kanji:
                dictionary_definitions += f'【{primary_reading}】'

            # The tags attached to the word i.e. Computing, Medicine, Biology
            if (tags := '; '.join(senses_info['tags'])):
                dictionary_definitions += f'\n*{tags}*'

            dictionary_definitions += f'\n{what_it_is}'

            # if jlpt_level:
            #     jlpt_level = jlpt_level.replace('jlpt-n', 'N')
            #     definition += f' [{jlpt_level}]'

            dictionary_definitions += f': {en_definitions}'

            if 'info' in senses_info and (definition_clarification := ', '.join(senses_info['info'])):
                dictionary_definitions += f'\n*{definition_clarification}*'

            dictionary_definitions += '\n\n'

        if len(dictionary_definitions) > MAX_DEFINITION_LENGTH:
            dictionary_definitions = dictionary_definitions[:MAX_DEFINITION_LENGTH]

        embed.description = dictionary_definitions
        embed.set_footer(text=guide['name'], icon_url=guide['favicon']['size16'])

        await ctx.send(embed=embed)

    @commands.command(name='urbandictionary', aliases=['wu', 'udictionary', 'ud'])
    async def search_urbandictionary(self, ctx: commands.Context, *, search_term: str):
        """Search a term in urbandictionary"""
        MAX_DEFINITION_LENGTH = 2048
        guide = self.bot.assets['urban_dictionary']
        search_term = search_term.lower()
        search_encoded = urllib.parse.quote_plus(search_term)
        user_search = guide['search_url'] + search_encoded

        if not (js := (await net_core.http_request(user_search, json=True)).json):
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if not 'list' in js or not js['list']:
            return await ctx.send(self.botstatus.get_quote('dictionary_no_results'))

        definition_embeds: list[discord.Embed] = []
        embed = discord.Embed()
        embed.title = search_term
        embed.url = guide['dictionary_url'] + search_encoded
        embed.description = ''
        definition_embeds.append(embed)
        index_placeholder = '<<INDEX>>'

        for i, entry in enumerate(js['list'][:3]):
            definition = entry['definition']
            example = entry['example']

            string_to_add = f"**{index_placeholder}. {self.strip_dictionary_oddities(definition, 'urban')}**\n\n"
            string_to_add += self.strip_dictionary_oddities(example, 'urban') + '\n\n'

            if len(string_to_add) - len(index_placeholder) + 1 > MAX_DEFINITION_LENGTH:
                string_to_add = string_to_add[:MAX_DEFINITION_LENGTH]
                await ctx.send('What a massive definition...')

            if i > 0 and len(embed.description) + len(string_to_add) - len(index_placeholder) + 1 > MAX_DEFINITION_LENGTH:
                definition_embeds.append(discord.Embed(description=string_to_add))
            else:
                embed.description += string_to_add

        definition_embeds[-1].set_footer(text=guide['name'], icon_url=guide['favicon']['size16'])

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

    @commands.command(name='dictionary', aliases=['d', 'word', 'w'])
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
                embed.description += f"\n**{subcategory_text}**\n{self.strip_dictionary_oddities(similar_meaning_string, 'merriam')}"

            # Add etymology
            if 'et' in category:
                etymology = category['et']
                embed.description += f"\n**etymology**\n{self.strip_dictionary_oddities(etymology[0][1], 'merriam')}\n\n"
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
    await bot.add_cog(InfoLookup(bot))
