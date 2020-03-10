"""Manage image board operations"""
import random
import re
import typing

import commentjson
import discord

import koabot.koakuma
import koabot.net


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

    post_id = koabot.koakuma.get_post_id(url, id_start, id_end, has_regex=end_regex)

    if not post_id:
        return

    post = await board_search(board=board, post_id=post_id)

    if not post:
        return

    on_nsfw_channel = channel.is_nsfw()

    if 'post' in post:
        post = post['post']

    if post['rating'] is not 's' and not on_nsfw_channel:
        embed = discord.Embed()
        if 'nsfw_placeholder' in koabot.koakuma.bot.assets[board]:
            embed.set_image(url=koabot.koakuma.bot.assets[board]['nsfw_placeholder'])
        else:
            embed.set_image(url=koabot.koakuma.bot.assets['default']['nsfw_placeholder'])

        content = '%s %s' % (msg.author.mention, random.choice(koabot.koakuma.bot.quotes['improper_content_reminder']))
        await koabot.koakuma.koa_is_typing_a_message(channel, content=content, embed=embed, rnd_duration=[1, 2])

    if board == 'e621':
        if post['relationships']['has_active_children']:
            search = 'parent:%s order:id' % post['id']
        elif post['relationships']['parent_id']:
            search = [
                'id:%s' % post['relationships']['parent_id'],
                'parent:%s order:id -id:%s' % (post['relationships']['parent_id'], post['id'])
            ]
        else:
            if post_is_missing_preview(post, board=board):
                if post['rating'] is 's' or on_nsfw_channel:
                    await send_board_posts(channel, post, board=board)
            return
    else:
        if post['has_children']:
            search = 'parent:%s order:id -id:%s' % (post['id'], post['id'])
        elif post['parent_id']:
            search = 'parent:%s order:id -id:%s' % (post['parent_id'], post['id'])
        else:
            if post_is_missing_preview(post, board=board):
                if post['rating'] is 's' or on_nsfw_channel:
                    await send_board_posts(channel, post, board=board)
            return

    # If there's multiple searches, put them all in the posts list
    if isinstance(search, typing.List):
        posts = []
        for query in search:
            results = await board_search(board=board, tags=query, include_nsfw=on_nsfw_channel)
            posts.extend(results['posts'])
    else:
        posts = await board_search(board=board, tags=search, include_nsfw=on_nsfw_channel)

    if 'posts' in posts:
        posts = posts['posts']

    post_included_in_results = False
    if post_is_missing_preview(post, board=board) and posts:
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
            content = random.choice(koabot.koakuma.bot.quotes['cannot_show_nsfw_gallery'])
        else:
            content = random.choice(koabot.koakuma.bot.quotes['rude_cannot_show_nsfw_gallery'])

        await koabot.koakuma.koa_is_typing_a_message(channel, content=content, rnd_duration=[1, 2])


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

    if 'posts' in posts:
        posts = posts['posts']

    await send_board_posts(ctx, posts, board=board)


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
            return await koabot.net.http_request(url, auth=koabot.koakuma.bot.danbooru_auth, json=True, err_msg='error fetching post #' + post_id)
        elif tags:
            if include_nsfw:
                url = 'https://danbooru.donmai.us'
            else:
                url = 'https://safebooru.donmai.us'

            return await koabot.net.http_request(url + '/posts.json', auth=koabot.koakuma.bot.danbooru_auth, data=commentjson.dumps(data_arg), headers={'Content-Type': 'application/json'}, json=True, err_msg='error fetching search: ' + tags)
    elif board == 'e621':
        # e621 requires to know the User-Agent
        headers = koabot.koakuma.bot.assets['e621']['headers']

        if post_id:
            url = 'https://e621.net/posts/%s.json' % post_id
            return await koabot.net.http_request(url, auth=koabot.koakuma.bot.e621_auth, json=True, headers=headers, err_msg='error fetching post #' + post_id)
        elif tags:
            if include_nsfw:
                url = 'https://e621.net'
            else:
                url = 'https://e926.net'

            headers['Content-Type'] = 'application/json'
            return await koabot.net.http_request(url + '/posts.json', auth=koabot.koakuma.bot.e621_auth, data=commentjson.dumps(data_arg), headers=headers, json=True, err_msg='error fetching search: ' + tags)
    else:
        raise ValueError('Board "%s" can\'t be handled by the post searcher.' % board)


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

    print('Sending %s posts' % board)

    for post in posts:
        posts_processed += 1
        print('Parsing post #%i (%i/%i)...' % (post['id'], posts_processed, min(total_posts, max_posts)))

        denied_ext = ['webm']
        if 'file_ext' in post and post['file_ext'] in denied_ext:
            if board == 'danbooru':
                url = 'https://danbooru.donmai.us/posts/%i' % post['id']
            elif board == 'e621':
                url = 'https://e621.net/posts/%i' % post['id']

            await ctx.send(url)
            continue

        embed = generate_board_embed(post, board=board)

        if max_posts != 0:
            if posts_processed >= min(max_posts, total_posts):
                last_post = True

                if total_posts > max_posts:
                    embed.set_footer(
                        text='%i+ remaining' % (total_posts - max_posts),
                        icon_url=koabot.koakuma.bot.assets[board]['favicon']['size16'])
                else:
                    embed.set_footer(
                        text=koabot.koakuma.bot.assets[board]['name'],
                        icon_url=koabot.koakuma.bot.assets[board]['favicon']['size16'])

        if not show_nsfw and post['rating'] is not 's':
            if 'nsfw_placeholder' in koabot.koakuma.bot.assets[board]:
                embed.set_image(url=koabot.koakuma.bot.assets[board]['nsfw_placeholder'])
            else:
                embed.set_image(url=koabot.koakuma.bot.assets['default']['nsfw_placeholder'])

            await ctx.send('<%s>' % embed.url, embed=embed)
        else:
            if board == 'danbooru':
                if post_is_missing_preview(post, board=board) or last_post:
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
        post_char = re.sub(r' \(.*?\)', '', koabot.koakuma.combine_tags(post['tag_string_character']))
        post_copy = koabot.koakuma.combine_tags(post['tag_string_copyright'])
        post_artist = koabot.koakuma.combine_tags(post['tag_string_artist'])
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

        embed_post_title += ' | Danbooru'
        if len(embed_post_title) >= koabot.koakuma.bot.assets['danbooru']['max_embed_title_length']:
            embed_post_title = embed_post_title[:koabot.koakuma.bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

        embed.title = embed_post_title
        embed.url = 'https://danbooru.donmai.us/posts/%i' % post['id']
    elif board == 'e621':
        embed.title = '#%s: %s - e621' % (post['id'], koabot.koakuma.combine_tags(post['tags']['artist']))
        embed.url = 'https://e621.net/posts/%i' % post['id']

    if 'failed_post_preview' in koabot.koakuma.bot.assets[board]:
        fileurl = koabot.koakuma.bot.assets[board]['failed_post_preview']
    else:
        fileurl = koabot.koakuma.bot.assets['default']['failed_post_preview']

    valid_urls_keys = ['large_file_url', 'file_url', 'preview_file_url', 'sample', 'file', 'preview']
    for key in valid_urls_keys:
        if key in post:
            if board == 'e621':
                fileurl = post[key]['url']
            else:
                fileurl = post[key]

            break

    embed.set_image(url=fileurl)
    return embed


def post_is_missing_preview(post, **kwargs):
    """Determine whether or not a post misses its preview
    Arguments:
        post::json object

    Keywords:
        board::str
            The board to check the rules with. Default is 'danbooru'
    """

    board = kwargs.get('board', 'danbooru')

    if board == 'e621':
        return koabot.koakuma.list_contains(post['tags']['general'], koabot.koakuma.bot.rules['no_preview_tags'][board]) and post['rating'] != 's'

    return koabot.koakuma.list_contains(post['tag_string_general'].split(), koabot.koakuma.bot.rules['no_preview_tags'][board]) or post['is_banned']
