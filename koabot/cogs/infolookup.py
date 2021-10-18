"""Search information and definitions"""
import math
import random
import re
import urllib

import discord
from discord.ext import commands
from mediawiki import MediaWiki
from mediawiki import exceptions as MediaExceptions

import koabot.utils.net as net_utils
from koabot import koakuma


class InfoLookup(commands.Cog):
    """InfoLookup class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wikipedia: MediaWiki = MediaWiki()

    @commands.command(name='wikipedia', aliases=['wk', 'wp'])
    async def search_wikipedia(self, ctx, *, search_term: str):
        """Search for articles in Wikipedia"""
        page_results = self.wikipedia.search(search_term)
        page_title = []

        try:
            page_title = page_results[0]
        except IndexError:
            bot_msg = "I can't find anything relevant. Sorry..."
            await ctx.send(bot_msg)
            return

        try:
            page = self.wikipedia.page(page_title, auto_suggest=False)
            summary = page.summary
            embed = discord.Embed()
            embed.title = page.title
            embed.url = page.url
            if len(summary) > 2000:
                summary = summary[:2000]
                for i in range(2000):
                    if summary[len(summary) - i - 1] != ' ':
                        continue

                    summary = summary[:len(summary) - i - 1] + '…'
                    break

            js = (await net_utils.http_request(f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}", json=True)).json
            if 'thumbnail' in js:
                embed.set_image(url=js['thumbnail']['source'])

            embed.description = summary
            embed.set_footer(text=self.bot.guides['explanation']['wikipedia-default']['embed']['footer_text'],
                             icon_url=self.bot.guides['explanation']['wikipedia-default']['favicon']['size16'])
            await ctx.send(embed=embed)
        except MediaExceptions.DisambiguationError as e:
            bot_msg = 'There are many definitions for that... do you see anything that matches?\n'

            for suggestion in e.options[0:3]:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)
        except MediaExceptions.PageError:
            bot_msg = "Oh, I can't find anything like that... how about these?\n"
            suggestions = self.wikipedia.search(search_term, results=3)

            for suggestion in suggestions:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)

    @commands.command(name='jisho', aliases=['j'])
    async def search_jisho(self, ctx, *, search_term: str):
        """Search a term in the japanese dictionary jisho"""

        search_term = search_term.lower()
        word_encoded = urllib.parse.quote_plus(search_term)
        user_search = self.bot.assets['jisho']['search_url'] + word_encoded

        js = (await net_utils.http_request(user_search, json=True)).json

        if not js:
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if js['meta']['status'] != 200:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        embed = discord.Embed()
        embed.title = search_term
        embed.url = self.bot.assets['jisho']['dictionary_url'] + urllib.parse.quote(search_term)
        embed.description = ''

        for word in js['data'][:4]:
            japanese_info = word['japanese'][0]
            senses_info = word['senses'][0]

            kanji = japanese_info.get('word', japanese_info.get('reading'))
            primary_reading = japanese_info.get('reading', None)
            jlpt_level = ', '.join(word['jlpt'])
            definitions = '; '.join(senses_info['english_definitions'])
            what_it_is = '; '.join(senses_info['parts_of_speech'])
            tags = '; '.join(senses_info['tags'])

            definition_clarification = 'info' in senses_info and ', '.join(senses_info['info']) or None

            embed.description += f'►{kanji}'

            if primary_reading and primary_reading != kanji:
                embed.description += f'【{primary_reading}】'

            if tags:
                embed.description += f'\n*{tags}*'

            embed.description += f'\n{what_it_is}'

            # if jlpt_level:
            #     jlpt_level = jlpt_level.replace('jlpt-n', 'N')
            #     embed.description += f' [{jlpt_level}]'

            embed.description += f': {definitions}'

            if definition_clarification:
                embed.description += f'\n*{definition_clarification}*'

            embed.description += '\n\n'

        if len(embed.description) > 2048:
            embed.description = embed.description[:2048]

        embed.set_footer(
            text=self.bot.assets['jisho']['name'],
            icon_url=self.bot.assets['jisho']['favicon']['size16'])

        await ctx.send(embed=embed)

    @commands.command(name='urbandictionary', aliases=['wu', 'udictionary', 'ud'])
    async def search_urbandictionary(self, ctx, *, search_term: str):
        """Search a term in urbandictionary"""

        search_term = search_term.lower()
        search_encoded = urllib.parse.quote_plus(search_term)
        user_search = self.bot.assets['urban_dictionary']['search_url'] + search_encoded

        js = (await net_utils.http_request(user_search, json=True)).json

        if not js:
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if not 'list' in js or not js['list']:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        definition_embeds = []
        embed = discord.Embed()
        embed.title = search_term
        embed.url = self.bot.assets['urban_dictionary']['dictionary_url'] + search_encoded
        embed.description = ''
        definition_embeds.append(embed)
        index_placeholder = '<<INDEX>>'

        for i, entry in enumerate(js['list'][:3]):
            definition = entry['definition']
            example = entry['example']

            string_to_add = f"**{index_placeholder}. {strip_dictionary_oddities(definition, 'urban')}**\n\n"
            string_to_add += strip_dictionary_oddities(example, 'urban') + '\n\n'

            if len(string_to_add) - len(index_placeholder) + 1 > 2048:
                string_to_add = string_to_add[:2048]
                await ctx.send('What a massive definition...')

            if i > 0 and len(embed.description) + len(string_to_add) - len(index_placeholder) + 1 > 2048:
                extra_embed = discord.Embed()
                extra_embed.description = string_to_add
                definition_embeds.append(extra_embed)
            else:
                embed.description += string_to_add

        definition_embeds[len(definition_embeds) - 1].set_footer(
            text=self.bot.assets['urban_dictionary']['name'],
            icon_url=self.bot.assets['urban_dictionary']['favicon']['size16'])

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
    async def search_english_word(self, ctx, *, search_term):
        """Search a term in merriam-webster's dictionary"""

        search_term = search_term.lower()
        search_encoded = urllib.parse.quote(search_term)
        user_search = f"{self.bot.assets['merriam-webster']['search_url']}/{search_encoded}?key={self.bot.auth_keys['merriam-webster']['key']}"

        js = (await net_utils.http_request(user_search, json=True)).json

        # Check if there are any results at all
        if not js:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        # If word has no direct definitions, they're word suggestions
        # (if there's no dicts, it's safe to assume they're strings)
        if not isinstance(js[0], dict):
            suggestions = js[:5]

            for i, suggestion in enumerate(suggestions):
                suggestions[i] = f'• {suggestion}'

            embed = discord.Embed()
            suggestion_list = '\n\n'.join(suggestions)
            embed.description = f"*{suggestion_list}*"
            embed.set_footer(
                text=self.bot.assets['merriam-webster']['name'],
                icon_url=self.bot.assets['merriam-webster']['favicon'])
            await ctx.send(random.choice(self.bot.quotes['dictionary_try_this']), embed=embed)
            return
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
        embed.url = f"{self.bot.assets['merriam-webster']['dictionary_url']}/{search_encoded}"
        embed.description = ''

        for category in js[:2]:
            if not 'def' in category or not 'hwi' in category:
                continue

            pronunciation = category['hwi']['hw']
            definitions = category['def']

            embed.description = f"{embed.description}►  *{pronunciation.replace('*', '・')}*"

            if 'fl' in category:
                embed.description = f"{embed.description}\n\n__**{category['fl'].upper()}**__"

            for subcategory in definitions:
                similar_meaning_string = ''
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
                embed.description = f"{embed.description}\n**{subcategory_text}**\n{strip_dictionary_oddities(similar_meaning_string, 'merriam')}"

            # Add etymology
            if 'et' in category:
                etymology = category['et']
                embed.description = f"{embed.description}\n**etymology**\n{strip_dictionary_oddities(etymology[0][1], 'merriam')}\n\n"
            else:
                embed.description = f"{embed.description}\n\n"

        # Embed descriptions longer than 2048 characters error out.
        if len(embed.description) > 2048:
            print("Definition over 2048 characters")
            embeds_to_send = math.ceil(len(embed.description) / 2048) - 1
            embeds_sent = 0

            dictionary_definitions = embed.description
            embed.description = dictionary_definitions[:2048]

            await ctx.send(embed=embed)

            # Print all the message across many embeds
            while embeds_sent < embeds_to_send:
                embeds_sent += 1

                embed = discord.Embed()
                embed.description = dictionary_definitions[2048 * embeds_sent:2048 * (embeds_sent + 1)]

                if embeds_sent == embeds_to_send:
                    embed.set_footer(
                        text=self.bot.assets['merriam-webster']['name'],
                        icon_url=self.bot.assets['merriam-webster']['favicon'])

                await ctx.send(embed=embed)
        else:
            embed.set_footer(
                text=self.bot.assets['merriam-webster']['name'],
                icon_url=self.bot.assets['merriam-webster']['favicon'])
            await ctx.send(embed=embed)


def strip_dictionary_oddities(txt: str, which: str):
    """Trim weird markup from dictionary entries"""

    if which == 'merriam':
        # Properly format words encased in weird characters

        # Remove all filler
        txt = re.sub(r'\{bc\}|\*', '', txt)

        while True:
            matches = re.findall(
                r'({[a-z_]+[\|}]+([a-zÀ-Ž\ \-\,]+)(?:{\/[a-z_]*|[a-z0-9\ \-\|\:\(\)]*)})', txt, re.IGNORECASE)

            if not matches:
                txt = re.sub(r'\{\/?[a-z\ _\-]+\}', '', txt)
                print(txt)
                return txt

            for match in matches:
                txt = txt.replace(match[0], f"*{match[1].upper()}*")
    elif which == 'urban':
        txt = txt.replace('*', '\*')

        matches = re.findall(r'(\[([\w\ ’\']+)\])', txt, re.IGNORECASE)
        for match in matches:
            txt = txt.replace(
                match[0], f"[{match[1]}]({koakuma.bot.assets['urban_dictionary']['dictionary_url']}{urllib.parse.quote(match[1])})")

        return txt


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(InfoLookup(bot))
