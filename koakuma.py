"""Koakuma bot"""
import asyncio
import math
import os
import random
import re
import subprocess
import typing
import urllib
from datetime import datetime

import aiohttp
import commentjson
import discord
import mysql.connector as mariadb
import pixivpy3
import tweepy
from discord.ext import commands

import converter
import net

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(SOURCE_DIR, 'config.jsonc')) as json_file:
    data = commentjson.load(json_file)

bot = commands.Bot(command_prefix='!', description='')
bot.launch_time = datetime.utcnow()
bot.__dict__.update(data)

twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'], bot.auth_keys['twitter']['consumer_secret'])
twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
twitter_api = tweepy.API(twit_auth, wait_on_rate_limit=True)

pixiv_api = pixivpy3.AppPixivAPI()

danbooru_auth = aiohttp.BasicAuth(login=bot.auth_keys['danbooru']['username'], password=bot.auth_keys['danbooru']['key'])
e621_auth = aiohttp.BasicAuth(login=bot.auth_keys['e621']['username'], password=bot.auth_keys['e621']['key'])

mariadb_connection = mariadb.connect(host=bot.database['host'], user=bot.database['username'], password=bot.database['password'])

last_channel = 0
last_channel_message_count = 0
last_channel_warned = False


@bot.command(name='jisho', aliases=['j'])
async def search_jisho(ctx, *word):
    """Search a term in the japanese dictionary jisho"""
    words = ' '.join(word).lower()
    word_encoded = urllib.parse.quote_plus(words)
    user_search = bot.assets['jisho']['search_url'] + word_encoded

    js = await net.http_request(user_search, json=True)

    if not js:
        await ctx.send('Error retrieving data from server.')
        return

    # Check if there are any results at all
    if js['meta']['status'] != 200:
        await ctx.send(random.choice(bot.quotes['dictionary_no_results']))
        return

    embed = discord.Embed()
    embed.title = words
    embed.url = bot.assets['jisho']['dictionary_url'] + urllib.parse.quote(words)
    embed.description = ''

    for entry in js['data'][:4]:
        kanji = 'word' in entry['japanese'][0] and entry['japanese'][0]['word'] or 'reading' in entry['japanese'][0] and entry['japanese'][0]['reading']
        primary_reading = 'reading' in entry['japanese'][0] and entry['japanese'][0]['reading'] or None
        jlpt_level = '; '.join(entry['jlpt'])
        definitions = '; '.join(entry['senses'][0]['english_definitions'])
        what_it_is = '; '.join(entry['senses'][0]['parts_of_speech'])
        tags = '; '.join(entry['senses'][0]['tags'])

        if tags:
            tags = '\n*%s*' % tags

        if primary_reading:
            embed.description += '►{kanji}【{reading}】\n{wis}: {}{} {}\n\n'.format(jlpt_level, definitions, tags, wis=what_it_is, reading=primary_reading, kanji=kanji)
        else:
            embed.description += '►{kanji}\n{wis}: {}{} {}\n\n'.format(jlpt_level, definitions, tags, wis=what_it_is, kanji=kanji)

    if len(embed.description) > 2048:
        embed.description = embed.description[:2048]

    await ctx.send(embed=embed)


@bot.command(name='urbandictionary', aliases=['wu', 'udictionary', 'ud'])
async def search_urbandictionary(ctx, *word):
    """Search a term in urbandictionary"""

    words = ' '.join(word).lower()
    word_encoded = urllib.parse.quote_plus(words)
    user_search = bot.assets['urban_dictionary']['search_url'] + word_encoded

    js = await net.http_request(user_search, json=True)

    if not js:
        await ctx.send('Error retrieving data from server.')
        return

    # Check if there are any results at all
    if not 'list' in js or not js['list']:
        await ctx.send(random.choice(bot.quotes['dictionary_no_results']))
        return

    embed = discord.Embed()
    embed.title = words
    embed.url = bot.assets['urban_dictionary']['dictionary_url'] + word_encoded
    embed.description = ''

    i = 0
    for entry in js['list'][:3]:
        i = i + 1
        definition = entry['definition']
        example = entry['example']

        embed.description += '**%i. %s**\n\n' % (i, formatDictionaryOddities(definition, 'urban'))
        embed.description += formatDictionaryOddities(example, 'urban') + '\n\n'

    if len(embed.description) > 2048:
        embed.description = embed.description[:2048]

    await ctx.send(embed=embed)


@bot.command(name='word', aliases=['w', 'dictionary'])
async def search_english_word(ctx, *word):
    """Search a term in merriam-webster's dictionary"""

    words = ' '.join(word).lower()
    word_encoded = urllib.parse.quote(words)
    user_search = '%s/%s?key=%s' % (bot.assets['merriam-webster']['search_url'], word_encoded, bot.auth_keys['merriam-webster']['key'])

    js = await net.http_request(user_search, json=True)

    if not js:
        await ctx.send('Oops. What?')
        return

    # Check if there are any results at all
    if not js:
        await ctx.send(random.choice(bot.quotes['dictionary_no_results']))
        return

    # If word has no direct definitions
    if not 'def' in js[0]:
        # If there's suggestions only
        if isinstance(js[0], str):
            suggestions = js[:5]

            for i, suggestion in enumerate(suggestions):
                suggestions[i] = '• ' + suggestion

            embed = discord.Embed()
            embed.description = '*%s*' % '\n\n'.join(suggestions)
            await ctx.send(random.choice(bot.quotes['dictionary_try_this']), embed=embed)
            return
        # If there's suggestions to a different grammatical tense
        else:
            tense = js[0]['cxs'][0]
            suggested_tense_word = tense['cxtis'][0]['cxt']
            await ctx.invoke(bot.get_command('word'), suggested_tense_word)
            return

    embed = discord.Embed()
    embed.title = words
    embed.url = '%s/%s' % (bot.assets['merriam-webster']['dictionary_url'], word_encoded)
    embed.description = ''

    for category in js[:2]:
        if not 'def' in category or not 'hwi' in category:
            continue

        pronunciation = category['hwi']['hw']
        definitions = category['def']

        embed.description = '%s►  *%s*' % (embed.description, pronunciation.replace('*', '・'))

        if 'fl' in category:
            embed.description = '%s\n\n__**%s**__' % (embed.description, category['fl'].upper())

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
                    similar_meaning_string += '%s: %s\n' % (meaning_position, definition)

            embed.description = '%s\n**%s**\n%s' % (embed.description, 'vd' in subcategory and subcategory['vd']
                                                    or 'definition', formatDictionaryOddities(similar_meaning_string, 'merriam'))

        # Add etymology
        if 'et' in category:
            etymology = category['et']
            embed.description = '%s\n**%s**\n%s\n\n' % (embed.description, 'etymology', formatDictionaryOddities(etymology[0][1], 'merriam'))
        else:
            embed.description = '%s\n\n' % embed.description

    # Embed descriptions longer than 2048 characters error out.
    if len(embed.description) > 2048:
        embeds_to_send = math.ceil(len(embed.description) / 2048) - 1
        embeds_sent = 0

        dictionary_definitions = embed.description
        embed.description = dictionary_definitions[0:2048]

        await ctx.send(embed=embed)

        # Print all the message across many embeds
        while embeds_sent < embeds_to_send:
            embeds_sent += 1

            embed = discord.Embed()
            embed.description = dictionary_definitions[2048 * embeds_sent:2048 * (embeds_sent + 1)]
            await ctx.send(embed=embed)
    else:
        await ctx.send(embed=embed)


def formatDictionaryOddities(txt, which):
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
            txt = txt.replace(match[0], '[%s](%s%s)' % (match[1], bot.assets['urban_dictionary']['dictionary_url'], urllib.parse.quote(match[1])))

        return txt


@bot.command(name='e621', aliases=['e6'])
async def search_e621(ctx, *args):
    """Search on e621!"""
    await search_board(ctx, args, board='e621')


@bot.command(name='danbooru', aliases=['dan'])
async def search_danbooru(ctx, *args):
    """Search on danbooru!"""
    await search_board(ctx, args)


async def search_board(ctx, tags, board='danbooru'):
    """Search on image boards!
    Arguments:
        ctx
            The context to interact with the discord API
        tags::*args (list)
            List of the tags sent by the user
        board::str
            The board to manage. Default is 'danbooru'
    """

    search = ' '.join(tags)
    print('User searching for: ' + search)

    on_nsfw_channel = ctx.channel.is_nsfw()

    async with ctx.typing():
        posts = await board_search(board=board, tags=search, limit=3, random=True, include_nsfw=on_nsfw_channel)

    if not posts:
        await ctx.send('Sorry, nothing found!')
        return

    await send_board_posts(ctx, posts, board=board)


def list_contains(lst, items_to_be_matched):
    """Helper function for checking if a list contains any elements of another list"""
    for item in items_to_be_matched:
        if item in lst:
            return True

    return False


def danbooru_post_has_missing_preview(post):
    """Determine whether or not a post misses its preview"""
    return list_contains(post['tag_string_general'].split(), bot.rules['no_preview_tags']) or post['is_banned']


async def send_board_posts(ctx, posts, **kwargs):
    """Handle sending posts retrieved from image boards
    Arguments:
        ctx
            The context to interact with the discord API
        posts::list or json object
            The post(s) to be sent to a channel

    Keywords:
        board::str
            The board to manage. Default is 'danbooru'
        show_nsfw::bool
            Whether or not nsfw posts should have their previews shown. Default is True
        max_posts::int
            How many posts should be shown before showing how many of them were cut-off.
            If max_posts is set to 0 then no footer will be shown and no posts will be omitted.
    """

    board = kwargs.get('board', 'danbooru')
    show_nsfw = kwargs.get('show_nsfw', True)
    max_posts = kwargs.get('max_posts', 4)

    if not isinstance(posts, typing.List):
        posts = [posts]

    total_posts = len(posts)
    posts_processed = 0
    last_post = False

    if max_posts != 0:
        posts = posts[:max_posts]

    for post in posts:
        posts_processed += 1
        print('Parsing post #%i (%i/%i)...' % (post['id'], posts_processed, min(total_posts, max_posts)))

        denied_ext = ['webm']
        if post['file_ext'] in denied_ext:
            if board == 'danbooru':
                url = 'https://danbooru.donmai.us/posts/%i' % post['id']
            elif board == 'e621':
                url = 'https://e621.net/post/show/%i' % post['id']

            await ctx.send(url)
            continue

        embed = generate_board_embed(post, board=board)

        if max_posts != 0:
            if posts_processed >= min(max_posts, total_posts):
                last_post = True

                if total_posts > max_posts:
                    embed.set_footer(
                        text='%i+ remaining' % (total_posts - max_posts),
                        icon_url=bot.assets[board]['favicon']
                    )
                else:
                    embed.set_footer(
                        text=bot.assets[board]['name'],
                        icon_url=bot.assets[board]['favicon']
                    )

        if not show_nsfw and post['rating'] is not 's':
            embed.set_image(url=bot.assets[board]['nsfw_placeholder'])
            await ctx.send('<%s>' % embed.url, embed=embed)
        else:
            if board == 'danbooru':
                if danbooru_post_has_missing_preview(post) or last_post:
                    await ctx.send('<%s>' % embed.url, embed=embed)
                else:
                    await ctx.send(embed.url)
            elif board == 'e621':
                await ctx.send('<%s>' % embed.url, embed=embed)

        print('Post #%i complete' % post['id'])


def generate_board_embed(post, **kwargs):
    """Generate embeds for image board post urls
    Arguments:
        post
            The post object

    Keywords:
        board::str
            The board to handle. Default is 'danbooru'
    """

    board = kwargs.get('board', 'danbooru')
    embed = discord.Embed()

    if board == 'danbooru':
        post_char = re.sub(r' \(.*?\)', '', combine_tags(post['tag_string_character']))
        post_copy = combine_tags(post['tag_string_copyright'])
        post_artist = combine_tags(post['tag_string_artist'])
        embed_post_title = ''

        if post_char:
            embed_post_title += post_char

        if post_copy:
            if not post_char:
                embed_post_title += post_copy
            else:
                embed_post_title += ' (%s)' % post_copy

        if post_artist:
            embed_post_title += ' drawn by ' + post_artist

        if not post_char and not post_copy and not post_artist:
            embed_post_title += '#%i' % post['id']

        embed_post_title += ' - Danbooru'
        if len(embed_post_title) >= bot.assets['danbooru']['max_embed_title_length']:
            embed_post_title = embed_post_title[:bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

        embed.title = embed_post_title
        embed.url = 'https://danbooru.donmai.us/posts/%i' % post['id']
    elif board == 'e621':
        embed.title = '#%s: %s - e621' % (post['id'], combine_tags(post['artist']))
        embed.url = 'https://e621.net/post/show/%i' % post['id']

    fileurl = bot.koa['failed_post_preview']

    valid_urls_keys = ['large_file_url', 'sample_url', 'file_url']
    for key in valid_urls_keys:
        if key in post:
            fileurl = post[key]
            break

    embed.set_image(url=fileurl)
    return embed


@bot.command(name='temperature', aliases=['temp'])
async def report_bot_temp(ctx):
    """Show the bot's current temperature"""

    try:
        current_temp = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, universal_newlines=True)
    except FileNotFoundError:
        current_temp = subprocess.run(['sensors'], stdout=subprocess.PIPE, universal_newlines=True)

    await ctx.send(current_temp.stdout)


@bot.command(name='last')
async def talk_status(ctx):
    """Mention a brief summary of the last used channel"""
    await ctx.send('Last channel: %s\nCurrent count there: %s' % (last_channel, last_channel_message_count))


@bot.command(aliases=['ava'])
async def avatar(ctx):
    """Display the avatar of an user"""

    if ctx.message.mentions:
        for mention in ctx.message.mentions:
            embed = discord.Embed()
            embed.set_image(url=mention.avatar_url)
            embed.set_author(
                name='%s #%i' % (mention.name, int(mention.discriminator)),
                icon_url=mention.avatar_url
            )
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed()
        embed.set_image(url=ctx.message.author.avatar_url)
        embed.set_author(
            name='%s #%i' % (ctx.message.author.name, int(ctx.message.author.discriminator)),
            icon_url=ctx.message.author.avatar_url
        )
        await ctx.send(embed=embed)


@bot.command()
async def uptime(ctx):
    """Mention the current uptime"""

    delta_uptime = datetime.utcnow() - bot.launch_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    await ctx.send('I\'ve been running for %i days, %i hours, %i minutes and %i seconds.' % (days, hours, minutes, seconds))


async def board_search(**kwargs):
    """Board searches handler
    Keywords:
        board::str
            Specify what board to search on. Default is 'danbooru'
        post_id::int
            Used for searching by post id on a board
        tags::str
            Used for searching with tags on a board
        limit::int
            How many images to retrieve. Default is 5
        random::bool
            Pick at random from results. Default is False
        include_nsfw::bool
            Whether or not the search will use safe versions of boards. Default is False

    Returns:
        json::dict
    """

    board = kwargs.get('board', 'danbooru')
    post_id = kwargs.get('post_id')
    tags = kwargs.get('tags')
    limit = kwargs.get('limit', 5)
    random_arg = kwargs.get('random', False)
    include_nsfw = kwargs.get('include_nsfw', False)

    data_arg = {
        'tags': tags,
        'limit': limit,
        'random': random_arg
    }

    if board == 'danbooru':

        if post_id:
            url = 'https://danbooru.donmai.us/posts/%s.json' % post_id
            return await net.http_request(url, auth=danbooru_auth, json=True, err_msg='error fetching post #' + post_id)
        elif tags:
            if include_nsfw:
                url = 'https://danbooru.donmai.us'
            else:
                url = 'https://safebooru.donmai.us'

            return await net.http_request(url + '/posts.json', auth=danbooru_auth, data=commentjson.dumps(data_arg), headers={'Content-Type': 'application/json'}, json=True, err_msg='error fetching search: ' + tags)
    elif board == 'e621':
        # e621 requires to know the User-Agent
        headers = {'User-Agent': bot.auth_keys['e621']['user-agent']}

        if post_id:
            url = 'https://e621.net/post/show/%s.json' % post_id
            return await net.http_request(url, auth=e621_auth, json=True, headers=headers, err_msg='error fetching post #' + post_id)
        elif tags:
            if include_nsfw:
                url = 'https://e621.net'
            else:
                url = 'https://e926.net'

            headers['Content-Type'] = 'application/json'
            return await net.http_request(url + '/post/index.json', auth=e621_auth, data=commentjson.dumps(data_arg), headers=headers, json=True, err_msg='error fetching search: ' + tags)
    else:
        raise ValueError('Board "%s" can\'t be handled by the post searcher.' % board)


async def get_danbooru_gallery(msg, url):
    """Automatically fetch and post any image galleries from danbooru"""
    await get_board_gallery(msg.channel, msg, url, id_start='/posts/', id_end='?')


async def get_imgur_gallery(msg, url):
    """Automatically fetch and post any image galleries from imgur"""

    channel = msg.channel

    album_id = get_post_id(url, ['/a/', '/gallery/'], '?')
    if not album_id:
        return

    search_url = bot.assets['imgur']['album_url'].format(album_id)
    api_result = await net.http_request(search_url, headers={'Authorization': 'Client-ID ' + bot.auth_keys['imgur']['client_id']}, json=True)

    if not api_result or api_result['status'] != 200:
        return

    total_album_pictures = len(api_result['data']) - 1

    if total_album_pictures < 1:
        return

    pictures_processed = 0
    for image in api_result['data'][1:5]:
        pictures_processed += 1

        embed = discord.Embed()
        embed.set_image(
            url=image['link']
        )

        if pictures_processed >= min(4, total_album_pictures):
            remaining_footer = ''

            if total_album_pictures > 4:
                remaining_footer = '%i+ remaining' % (total_album_pictures - 4)
            else:
                remaining_footer = bot.assets['imgur']['name']

            embed.set_footer(
                text=remaining_footer,
                icon_url=bot.assets['imgur']['favicon']
            )

        await channel.send(embed=embed)


async def generate_pixiv_embed(post, user):
    """Generate embeds for pixiv urls
    Arguments:
        post
            The post object
        user
            The artist of the post
    """

    img_url = post.image_urls.medium
    image_filename = get_file_name(img_url)
    image = await net.fetch_image(img_url, headers={'Referer': 'https://app-api.pixiv.net/'})

    embed = discord.Embed()
    embed.set_author(
        name=user.name,
        url='https://www.pixiv.net/member.php?id=%i' % user.id
    )
    embed.set_image(url='attachment://' + image_filename)
    return embed, image, image_filename


async def get_pixiv_gallery(msg, url):
    """Automatically fetch and post any image galleries from pixiv"""

    channel = msg.channel

    post_id = get_post_id(url, ['illust_id=', '/artworks/'], '&')
    if not post_id:
        return

    print('Now starting to process pixiv link #' + post_id)
    # Login
    if pixiv_api.access_token is None:
        pixiv_api.login(bot.auth_keys['pixiv']['username'], bot.auth_keys['pixiv']['password'])
    else:
        pixiv_api.auth()

    try:
        illust_json = pixiv_api.illust_detail(post_id, req_auth=True)
    except pixivpy3.PixivError as e:
        await channel.send('Odd...')
        print(e)
        return

    print(illust_json)
    if 'illust' not in illust_json:
        # too bad
        print('Invalid Pixiv id #' + post_id)
        return

    print('Pixiv auth passed! (for #%s)' % post_id)

    illust = illust_json.illust
    if illust.x_restrict != 0 and not channel.is_nsfw():
        embed = discord.Embed()
        embed.set_image(url=bot.assets['danbooru']['nsfw_placeholder'])
        content = '%s %s' % (msg.author.mention, random.choice(bot.quotes['improper_content_reminder']))
        await koa_is_typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])
        return

    temp_message = await channel.send('***%s***' % random.choice(bot.quotes['processing_long_task']))
    async with channel.typing():
        total_illust_pictures = illust.page_count

        if total_illust_pictures > 1:
            pictures = illust.meta_pages
        else:
            pictures = [illust]

        pictures_processed = 0
        for picture in pictures[:4]:
            pictures_processed += 1
            print('Retrieving picture from #%s...' % post_id)

            (embed, image, filename) = await generate_pixiv_embed(picture, illust.user)
            print('Retrieved more from #%s (maybe)' % post_id)

            if pictures_processed >= min(4, total_illust_pictures):
                remaining_footer = ''

                if total_illust_pictures > 4:
                    remaining_footer = '%i+ remaining' % (total_illust_pictures - 4)
                else:
                    remaining_footer = bot.assets['pixiv']['name']

                embed.set_footer(
                    text=remaining_footer,
                    icon_url=bot.assets['pixiv']['favicon']
                )
            await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)

    await temp_message.delete()
    print('DONE PIXIV!')


async def get_board_gallery(channel, msg, url, **kwargs):
    """Automatically automatic
    Keywords:
        board::str
            The board to handle. Default is 'danbooru'
        id_start::str
            The point at which an url is stripped from
        id_end::str
            The point at which an url is stripped to
        end_regex::bool
            Whether or not id_end is regex. Default is False
    """

    board = kwargs.get('board', 'danbooru')
    id_start = kwargs.get('id_start')
    id_end = kwargs.get('id_end')
    end_regex = kwargs.get('end_regex', False)

    post_id = get_post_id(url, id_start, id_end, has_regex=end_regex)

    if not post_id:
        return

    post = await board_search(board=board, post_id=post_id)

    if not post:
        return

    on_nsfw_channel = channel.is_nsfw()

    if post['rating'] is not 's' and not on_nsfw_channel:
        embed = discord.Embed()
        embed.set_image(url=bot.assets[board]['nsfw_placeholder'])
        content = '%s %s' % (msg.author.mention, random.choice(bot.quotes['improper_content_reminder']))
        await koa_is_typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

    if post['has_children']:
        search = board == 'danbooru' and 'parent:%s order:id -id:%s' % (post['id'], post['id']) or 'parent:%s' % post['id']
    elif post['parent_id']:
        search = board == 'danbooru' and 'parent:%s order:id -id:%s' % (post['parent_id'], post['id']) or 'id:%s' % post['parent_id']
    else:
        if board == 'danbooru' and danbooru_post_has_missing_preview(post) or board == 'e621':
            if post['rating'] is 's' or on_nsfw_channel:
                await send_board_posts(channel, post, board=board)
        return

    posts = await board_search(board=board, tags=search, include_nsfw=on_nsfw_channel)

    post_included_in_results = False
    if board == 'danbooru' and danbooru_post_has_missing_preview(post) and posts or board == 'e621' and posts:
        if post['rating'] is 's' or on_nsfw_channel:
            post_included_in_results = True
            post = [post]
            post.extend(posts)
            posts = post

    if posts:
        if post_included_in_results:
            await send_board_posts(channel, posts, board=board, show_nsfw=on_nsfw_channel, max_posts=5)
        else:
            await send_board_posts(channel, posts, board=board, show_nsfw=on_nsfw_channel)
    else:
        if post['rating'] is 's':
            content = random.choice(bot.quotes['cannot_show_nsfw_gallery'])
        else:
            content = random.choice(bot.quotes['rude_cannot_show_nsfw_gallery'])

        await koa_is_typing_a_message(channel, content=content, rnd_duration=[1, 2])


async def get_e621_gallery(msg, url):
    """Automatically fetch a bigger preview and gallery from e621"""
    await get_board_gallery(msg.channel, msg, url, board='e621', id_start='/show/', id_end=r'^[0-9]+', end_regex=True)


async def get_sankaku_post(msg, url):
    """Automatically fetch a bigger preview and gallery from Sankaku Complex"""

    channel = msg.channel

    post_id = get_post_id(url, '/show/', '?')
    if not post_id:
        return

    search_url = bot.assets['sankaku']['id_search_url'] + post_id
    api_result = await net.http_request(search_url, json=True)

    if not api_result or 'code' in api_result:
        print('Sankaku error\nCode #{}'.format(api_result['code']))
        return

    embed = discord.Embed()
    embed.set_image(
        url=api_result['preview_url']
    )
    embed.set_footer(
        text=bot.assets['sankaku']['name'],
        icon_url=bot.assets['sankaku']['favicon']
    )

    await channel.send(embed=embed)


async def get_deviantart_post(msg, url):
    """Automatically fetch post from deviantart"""

    channel = msg.channel

    post_id = get_post_id(url, '/art/', r'[0-9]+$', has_regex=True)
    if not post_id:
        return

    search_url = bot.assets['deviantart']['search_url_extended'].format(post_id)

    api_result = await net.http_request(search_url, json=True, err_msg='error fetching post #' + post_id)

    if not api_result['deviation']['isMature']:
        return

    for file in api_result['deviation']['files']:
        if file['type'] == 'preview':
            preview_url = file['src']
            break

    embed = discord.Embed()
    embed.set_author(
        name=api_result['deviation']['author']['username'],
        url='https://www.deviantart.com/' + api_result['deviation']['author']['username'],
        icon_url=api_result['deviation']['author']['usericon'])
    embed.set_image(url=preview_url)
    embed.set_footer(
        text=bot.assets['deviantart']['name'],
        icon_url=bot.assets['deviantart']['favicon']
    )

    await channel.send(embed=embed)


async def get_picarto_stream_preview(msg, url):
    """Automatically fetch a preview of the running stream"""

    channel = msg.channel
    post_id = get_post_id(url, '.tv/', '&')

    if not post_id:
        return

    picarto_request = await net.http_request('https://api.picarto.tv/v1/channel/name/' + post_id, json=True)

    if not picarto_request['online']:
        return

    image = await net.fetch_image(picarto_request['thumbnails']['web'])
    filename = get_file_name(picarto_request['thumbnails']['web'])

    embed = discord.Embed()
    embed.set_author(name=post_id, url='https://picarto.tv/' + post_id, icon_url=picarto_request['avatar'])
    embed.description = '**%s**' % picarto_request['title']
    embed.set_image(url='attachment://' + filename)
    embed.set_footer(text=bot.assets['picarto']['name'], icon_url=bot.assets['picarto']['favicon'])
    await channel.send(file=discord.File(fp=image, filename=filename), embed=embed)


def get_post_id(url, words_to_match, trim_to, has_regex=False):
    """Get post id from url
    Arguments:
        url::str
        words_to_match::str or list
        trim_to::str or regex
        has_regex::bool
    """

    if not isinstance(words_to_match, typing.List):
        words_to_match = [words_to_match]

    matching_word = False
    for v in words_to_match:
        if v in url:
            matching_word = v

    if not matching_word:
        return

    if has_regex:
        return re.findall(trim_to, url.split(matching_word)[1])[0]

    return url.split(matching_word)[1].split(trim_to)[0]


def combine_tags(tags):
    """Combine tags and give them a readable format
    Arguments:
        tags::str or list
    """

    if isinstance(tags, typing.List):
        tag_list = tags
    else:
        tag_list = tags.split()[:5]

    if len(tag_list) > 1:
        joint_tags = ', '.join(tag_list[:-1])
        joint_tags += ' and ' + tag_list[-1]
        return joint_tags.strip().replace('_', ' ')

    return ''.join(tag_list).strip().replace('_', ' ')


def get_urls(string):
    """findall() has been used with valid conditions for urls in string"""

    regex_exp = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    matching_urls = re.findall(regex_exp, string)
    return matching_urls


def get_domains(lst):
    """Get domains from a link
    thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868"""

    domains = []

    for url in lst:
        domain = url.split('//')[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


def get_file_name(url):
    """Get file name from url"""

    return url.split('/')[-1]


async def convert_units(msg):
    """Convert units found to their opposite (SI <-> imp)"""

    imperial_units = [
        'feet',
        'inches',
        'miles',
        'pounds',
    ]
    si_units = [
        'meters',
        'centimeters',
        'kilometers',
        'kilograms'
    ]

    # Find all units
    units = converter.find_units(msg.content)

    if not units:
        return

    channel = msg.channel
    conversion_str = random.choice(bot.quotes['converting_units']) + '```'

    for quantity in units:
        if quantity[0] == 'footinches':
            value = quantity[1]
            value2 = quantity[2]

            converted_value = value * converter.ureg.foot + value2 * converter.ureg.inch
            conversion_str += ('\n{} {} → {}').format(value * converter.ureg.foot, value2 * converter.ureg.inch, converted_value.to_base_units())
            continue

        (unit, value) = quantity
        value = value * converter.ureg[unit]

        if unit in imperial_units:
            converted_value = value.to_base_units()
            converted_value = converted_value.to_compact()
        elif unit in si_units:
            if unit == 'kilometers':
                converted_value = value.to(converter.ureg.miles)
            elif unit == 'kilograms':
                converted_value = value.to(converter.ureg.pounds)
            elif value.magnitude >= 300:
                converted_value = value.to(converter.ureg.yards)
            else:
                converted_value = value.to(converter.ureg.feet)

        conversion_str += ('\n{} → {}').format(value, converted_value)

    # Random chance for final quote ([0..4])
    if random.randint(0, 4) == 4:
        conversion_str += '```\n' + random.choice(bot.quotes['converting_units_modest'])
    else:
        conversion_str += '```'

    await channel.send(conversion_str)


async def koa_is_typing_a_message(ctx, **kwargs):
    """Make Koakuma seem alive with a 'is typing' delay

    Keywords:
        content::str
            Message to be said.
        embed::discord.Embed
            Self-explanatory. Default is None.
        rnd_duration::list or int
            A list with two int values of what's the least that should be waited for to the most, chosen at random.
            If provided an int the 0 will be assumed at the start.
        min_duration::int
            The amount of time that will be waited regardless of rnd_duration.
    """

    content = kwargs.get('content')
    embed = kwargs.get('embed')
    rnd_duration = kwargs.get('rnd_duration')
    min_duration = kwargs.get('min_duration', 0)

    if isinstance(rnd_duration, int):
        rnd_duration = [0, rnd_duration]

    async with ctx.typing():
        if rnd_duration:
            time_to_wait = random.randint(rnd_duration[0], rnd_duration[1])
            if time_to_wait < min_duration:
                time_to_wait = min_duration
            await asyncio.sleep(time_to_wait)
        else:
            await asyncio.sleep(min_duration)

        if embed is not None:
            if content:
                await ctx.send(content, embed=embed)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(content)


async def check_live_streamers():
    """Checks every so often for streamers that have gone online"""

    await bot.wait_until_ready()

    online_streamers = []

    while not bot.is_closed():
        temp_online = []
        for streamer in online_streamers:
            if streamer['preserve']:
                streamer['preserve'] = False
                temp_online.append(streamer)

        online_streamers = temp_online

        twitch_search = 'https://api.twitch.tv/helix/streams?'

        for streamer in bot.tasks['streamer_activity']['streamers']:
            if streamer['platform'] == 'twitch':
                twitch_search += 'user_id=%s&' % streamer['user_id']

        twitch_query = await net.http_request(twitch_search, headers={'Client-ID': bot.auth_keys['twitch']['client_id']}, json=True)

        for streamer in twitch_query['data']:
            already_online = False

            for on_streamer in online_streamers:
                if streamer['id'] == on_streamer['streamer']['id']:
                    # streamer is already online, and it was already reported
                    on_streamer['preserve'] = True
                    on_streamer['announced'] = True
                    already_online = True

            if already_online:
                continue

            for config_streamers in bot.tasks['streamer_activity']['streamers']:
                if streamer['user_id'] == str(config_streamers['user_id']):
                    natural_name = 'casual_name' in config_streamers and config_streamers['casual_name'] or streamer['user_name']
                    break

            online_streamers.append({'platform': 'twitch', 'streamer': streamer, 'name': natural_name, 'preserve': True, 'announced': False})

        stream_announcements = []
        for streamer in online_streamers:
            if streamer['announced']:
                continue

            embed = discord.Embed()
            embed.set_author(name=streamer['streamer']['user_name'], url='https://www.twitch.tv/' + streamer['streamer']['user_name'])
            embed.set_footer(text=bot.assets['twitch']['name'], icon_url=bot.assets['twitch']['favicon'])

            # setting thumbnail size
            thumbnail_url = streamer['streamer']['thumbnail_url']
            thumbnail_url = thumbnail_url.replace('{width}', '600')
            thumbnail_url = thumbnail_url.replace('{height}', '350')
            thumbnail_file_name = get_file_name(thumbnail_url)
            image = await net.fetch_image(thumbnail_url)
            embed.set_image(url='attachment://' + thumbnail_file_name)

            stream_announcements.append({'message': '%s is now live!' % streamer['name'], 'embed': embed, 'image': image, 'filename': thumbnail_file_name})

        for channel in bot.tasks['streamer_activity']['channels_to_announce_on']:
            for batch in stream_announcements:
                channel = bot.get_channel(channel)
                if 'image' in batch:
                    await channel.send(batch['message'], file=discord.File(fp=batch['image'], filename=batch['filename']), embed=batch['embed'])
                else:
                    await channel.send(batch['message'], embed=batch['embed'])

        # check every 5 minutes
        await asyncio.sleep(60)


async def change_presence_periodically():
    """Changes presence at X time, once per day"""

    await bot.wait_until_ready()

    day = datetime.utcnow().day

    while not bot.is_closed():
        time = datetime.utcnow()

        # if it's time and it's not the same day
        if time.hour == bot.tasks['presence_change']['utc_hour'] and time.day != day:
            day = time.day
            await bot.change_presence(activity=discord.Game(name=random.choice(bot.quotes['playing_status'])))

        # check twice an hour
        await asyncio.sleep(60 * 30)


async def lookup_pending_posts():
    """Every 5 minutes search for danbooru posts"""

    await bot.wait_until_ready()

    pending_posts = []
    channel_categories = {}

    for channel_category, channel_list in bot.tasks['danbooru']['channels'].items():
        channel_categories[channel_category] = []
        for channel in channel_list:
            channel_categories[channel_category].append(bot.get_channel(int(channel)))

    while not bot.is_closed():
        posts = await board_search(tags=bot.tasks['danbooru']['tag_list'], limit=5, random=True)

        safe_posts = []
        nsfw_posts = []
        for post in posts:
            if not post['id'] in pending_posts:
                pending_posts.append(post['id'])
                url_to_append = 'https://danbooru.donmai.us/posts/%i' % post['id']

                if post['rating'] is 's':
                    safe_posts.append(url_to_append)
                else:
                    nsfw_posts.append(url_to_append)

        safe_posts = '\n'.join(safe_posts)
        nsfw_posts = '\n'.join(nsfw_posts)

        if safe_posts or nsfw_posts:
            for channel in channel_categories['safe_channels']:
                await channel.send(random.choice(bot.quotes['posts_to_approve']) + '\n' + safe_posts)

        if nsfw_posts:
            for channel in channel_categories['nsfw_channels']:
                await channel.send(random.choice(bot.quotes['posts_to_approve']) + '\n' + nsfw_posts)

        await asyncio.sleep(60 * 5)


@bot.event
async def on_message(msg):
    global last_channel, last_channel_message_count, last_channel_warned
    """Searches messages for urls and certain keywords"""

    # Prevent bot from spamming itself
    if msg.author.bot:
        return

    channel = msg.channel

    # Reference channels together
    for mentioned_channel in msg.channel_mentions:
        target_channel_msg = await mentioned_channel.send('Mention by {} from {}\n\nGo there:\n<{}>'.format(msg.author.mention, channel.mention, msg.jump_url))
        await channel.send('Mention by {} to {}\n\nGo there:\n<{}>'.format(msg.author.mention, mentioned_channel.mention, target_channel_msg.jump_url))

    # Test for units
    await convert_units(msg)

    # Test for image urls
    urls = get_urls(msg.content)
    if urls:
        domains = get_domains(urls)
        for i, domain in enumerate(domains):
            if bot.assets['pixiv']['domain'] in domain:
                await get_pixiv_gallery(msg, urls[i])

            if bot.assets['danbooru']['domain'] in domain:
                await get_danbooru_gallery(msg, urls[i])

            if bot.assets['e621']['domain'] in domain:
                await get_e621_gallery(msg, urls[i])

            if bot.assets['deviantart']['domain'] in domain:
                await get_deviantart_post(msg, urls[i])

            if bot.assets['imgur']['domain'] in domain:
                await get_imgur_gallery(msg, urls[i])

            if bot.assets['picarto']['domain'] in domain:
                await get_picarto_stream_preview(msg, urls[i])

            # if bot.assets['sankaku']['domain'] in domain:
            #     await get_sankaku_post(msg, urls[i])

    if last_channel != channel.id or urls or msg.attachments:
        last_channel = channel.id
        last_channel_message_count = 0
    else:
        last_channel_message_count += 1

    if str(channel.id) in bot.rules['quiet_channels']:
        if not last_channel_warned and last_channel_message_count >= bot.rules['quiet_channels'][str(channel.id)]['max_messages_without_embeds']:
            last_channel_warned = True
            await koa_is_typing_a_message(channel, content=random.choice(bot.quotes['quiet_channel_past_threshold']), rnd_duration=[1, 2])

    await bot.process_commands(msg)


@bot.event
async def on_ready():
    """On bot start"""

    print('ready!')
    # Change play status to something fitting
    await bot.change_presence(activity=discord.Game(name=random.choice(bot.quotes['playing_status'])))

bot.loop.create_task(check_live_streamers())
bot.loop.create_task(change_presence_periodically())
bot.run(bot.auth_keys['discord']['token'])
