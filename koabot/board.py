"""Manage image board operations"""
import typing

import commentjson

import koabot


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
        headers = koabot.koakuma.koabot.koakuma.bot.assets['e621']['headers']

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

        embed = koabot.koakuma.generate_board_embed(post, board=board)

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
                if koabot.board.post_is_missing_preview(post, board=board) or last_post:
                    await ctx.send('<%s>' % embed.url, embed=embed)
                else:
                    await ctx.send(embed.url)
            elif board == 'e621':
                await ctx.send('<%s>' % embed.url, embed=embed)

        print('Post #%i complete' % post['id'])
