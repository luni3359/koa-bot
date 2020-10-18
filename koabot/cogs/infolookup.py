"""Search information and definitions"""
import math
import random
import re
import typing
import urllib

import mediawiki
import discord
from discord.ext import commands

import koabot.koakuma as koakuma
import koabot.utils as utils


class InfoLookup(commands.Cog):
    """InfoLookup class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wikipedia = mediawiki.MediaWiki()

    @commands.command(name='wikipedia', aliases=['wk', 'wp'])
    async def search_wikipedia(self, ctx, *words):
        """Search for articles in Wikipedia"""
        search_term = ' '.join(words)

        page_results = self.wikipedia.search(search_term)
        page_title = page_results[0]

        try:
            page = self.wikipedia.page(page_title, auto_suggest=False)
            summary = page.summary

            if len(summary) > 2000:
                summary = summary[:2000]
                for i in range(2000):
                    if summary[len(summary) - i - 1] != ' ':
                        continue

                    summary = summary[:len(summary) - i - 1] + '…'
                    break

            await ctx.send(summary)
        except mediawiki.exceptions.DisambiguationError as e:
            bot_msg = 'There are many definitions for that... do you see anything that matches?\n'

            for suggestion in e.options[0:3]:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)
        except mediawiki.exceptions.PageError:
            bot_msg = 'Oh, I can\'t find anything like that... how about these?\n'
            suggestions = self.wikipedia.search(search_term, results=3)

            for suggestion in suggestions:
                bot_msg += f'* {suggestion}\n'

            await ctx.send(bot_msg)

    @commands.command(name='jisho', aliases=['j'])
    async def search_jisho(self, ctx, *word):
        """Search a term in the japanese dictionary jisho"""

        words = ' '.join(word).lower()
        word_encoded = urllib.parse.quote_plus(words)
        user_search = self.bot.assets['jisho']['search_url'] + word_encoded

        js = (await utils.net.http_request(user_search, json=True)).json

        if not js:
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if js['meta']['status'] != 200:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        embed = discord.Embed()
        embed.title = words
        embed.url = self.bot.assets['jisho']['dictionary_url'] + urllib.parse.quote(words)
        embed.description = ''

        for entry in js['data'][:4]:
            kanji = 'word' in entry['japanese'][0] and entry['japanese'][0]['word'] or 'reading' in entry['japanese'][0] and entry['japanese'][0]['reading']
            primary_reading = 'reading' in entry['japanese'][0] and entry['japanese'][0]['reading'] or None
            jlpt_level = '; '.join(entry['jlpt'])
            definitions = '; '.join(entry['senses'][0]['english_definitions'])
            what_it_is = '; '.join(entry['senses'][0]['parts_of_speech'])
            tags = '; '.join(entry['senses'][0]['tags'])

            if tags:
                tags = f'\n*{tags}*'

            if primary_reading:
                if jlpt_level:
                    jlpt_level = jlpt_level.replace('jlpt-n', 'N')
                    embed.description += f'►{kanji}【{primary_reading}】\n{what_it_is} [{jlpt_level}]: {definitions} {tags}\n\n'
                else:
                    embed.description += f'►{kanji}【{primary_reading}】\n{what_it_is}: {definitions} {tags}\n\n'
            else:
                embed.description += f'►{kanji}\n{what_it_is} [{jlpt_level}]: {definitions} {tags}\n\n'

        if len(embed.description) > 2048:
            embed.description = embed.description[:2048]

        embed.set_footer(
            text=self.bot.assets['jisho']['name'],
            icon_url=self.bot.assets['jisho']['favicon']['size16'])

        await ctx.send(embed=embed)

    @commands.command(name='urbandictionary', aliases=['wu', 'udictionary', 'ud'])
    async def search_urbandictionary(self, ctx, *word):
        """Search a term in urbandictionary"""

        words = ' '.join(word).lower()
        word_encoded = urllib.parse.quote_plus(words)
        user_search = self.bot.assets['urban_dictionary']['search_url'] + word_encoded

        js = (await utils.net.http_request(user_search, json=True)).json

        if not js:
            await ctx.send('Error retrieving data from server.')
            return

        # Check if there are any results at all
        if not 'list' in js or not js['list']:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        definition_embeds = []
        embed = discord.Embed()
        embed.title = words
        embed.url = self.bot.assets['urban_dictionary']['dictionary_url'] + word_encoded
        embed.description = ''
        definition_embeds.append(embed)
        index_placeholder = '<<INDEX>>'

        for i, entry in enumerate(js['list'][:3]):
            definition = entry['definition']
            example = entry['example']

            string_to_add = f"**{index_placeholder}. {formatDictionaryOddities(definition, 'urban')}**\n\n"
            string_to_add += formatDictionaryOddities(example, 'urban') + '\n\n'

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
    async def search_english_word(self, ctx, *word):
        """Search a term in merriam-webster's dictionary"""

        words = ' '.join(word).lower()
        word_encoded = urllib.parse.quote(words)
        user_search = f"{self.bot.assets['merriam-webster']['search_url']}/{word_encoded}?key={self.bot.auth_keys['merriam-webster']['key']}"

        js = (await utils.net.http_request(user_search, json=True)).json

        if not js:
            await ctx.send('Oops. What?')
            return

        # Check if there are any results at all
        if not js:
            await ctx.send(random.choice(self.bot.quotes['dictionary_no_results']))
            return

        # If word has no direct definitions
        if not 'def' in js[0]:
            # If there's suggestions only
            if isinstance(js[0], str):
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
            else:
                tense = js[0]['cxs'][0]
                suggested_tense_word = tense['cxtis'][0]['cxt']
                await ctx.send('Hmm... Let\'s see...')
                await ctx.invoke(self.bot.get_command('word'), suggested_tense_word)
                return

        embed = discord.Embed()
        embed.title = words
        embed.url = f"{self.bot.assets['merriam-webster']['dictionary_url']}/{word_encoded}"
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

                        if isinstance(meaning_item, typing.List):
                            meaning_item = meaning_item[0]

                        meaning_position = 'sn' in meaning_item and meaning_item['sn'] or '1'

                        if not meaning_position[0].isdigit():
                            meaning_position = '\u3000' + meaning_position

                        # Get definition
                        # What a mess
                        if isinstance(meaning_item, typing.List):
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

                        if isinstance(definition, typing.List):
                            definition = definition[0][0][1]

                        # Format bullet point
                        similar_meaning_string += f'{meaning_position}: {definition}\n'

                embed.description = '%s\n**%s**\n%s' % (embed.description, 'vd' in subcategory and subcategory['vd']
                                                        or 'definition', formatDictionaryOddities(similar_meaning_string, 'merriam'))

            # Add etymology
            if 'et' in category:
                etymology = category['et']
                embed.description = '%s\n**%s**\n%s\n\n' % (embed.description, 'etymology', formatDictionaryOddities(etymology[0][1], 'merriam'))
            else:
                embed.description = f'{embed.description}\n\n'

        # Embed descriptions longer than 2048 characters error out.
        if len(embed.description) > 2048:
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


def formatDictionaryOddities(txt: str, which: str):
    """Trim weird markup from dictionary entries"""

    if which == 'merriam':
        # Properly format words encased in weird characters

        # Remove all filler
        txt = re.sub(r'\{bc\}|\*', '', txt)

        while True:
            matches = re.findall(r'({[a-z_]+[\|}]+([a-zÀ-Ž\ \-\,]+)(?:{\/[a-z_]*|[a-z0-9\ \-\|\:\(\)]*)})', txt, re.IGNORECASE)

            if not matches:
                txt = re.sub(r'\{\/?[a-z\ _\-]+\}', '', txt)
                print(txt)
                return txt

            for match in matches:
                txt = txt.replace(match[0], '*%s*' % match[1].upper())
    elif which == 'urban':
        txt = txt.replace('*', '\*')

        matches = re.findall(r'(\[([\w\ ’\']+)\])', txt, re.IGNORECASE)
        for match in matches:
            txt = txt.replace(match[0], f"[{match[1]}]({koakuma.bot.assets['urban_dictionary']['dictionary_url']}{urllib.parse.quote(match[1])})")

        return txt


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(InfoLookup(bot))
