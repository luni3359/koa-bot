"""Koakuma bot"""
import glob
import html
import itertools
import os
import random
import re
import shutil
from datetime import datetime

import aiohttp
import appdirs
import basc_py4chan
import commentjson
import discord
import forex_python.converter as currency
import mysql.connector as mariadb
import pixivpy3
import tweepy
from discord.ext import commands
from num2words import num2words

import koabot.converter
import koabot.tasks
import koabot.utils
from koabot.patterns import *

bot = commands.Bot(command_prefix='!', description='')
SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
BOT_DIRNAME = 'koa-bot'

# Make config dir if it doesn't exist
CONFIG_DIR = appdirs.user_config_dir(BOT_DIRNAME)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Make cache dir if it doesn't exist
CACHE_DIR = appdirs.user_cache_dir(BOT_DIRNAME)
os.makedirs(CACHE_DIR, exist_ok=True)


@bot.command()
async def roll(ctx, *dice):
    """Rolls one or many dice"""

    if len(dice) < 1:
        await ctx.send('Please specify what you want to roll.')
        return

    dice_matches = re.findall(DICE_PATTERN, ' '.join(dice))

    if not dice_matches:
        await ctx.send('Sorry, I can\'t do that...')
        return

    dice_single_or_many = len(dice_matches) > 1 or (dice_matches[0][0] and int(dice_matches[0][0]) > 1)
    message = '>>> {} rolled the {}.\n'.format(ctx.author.mention, dice_single_or_many and 'dice' or 'die')
    pip_sum = 0

    for match in dice_matches:
        quantity = match[0] and int(match[0]) or 1
        pips = match[1] and int(match[1]) or 1
        bonus_points = match[2] and int(match[2]) or 0

        message += '{} {}-sided {} for a '.format(num2words(quantity).capitalize(), pips, quantity > 1 and 'dice' or 'die')

        for i in range(0, quantity):
            die_roll = random.randint(1, pips)

            if i == quantity - 1:
                if quantity == 1:
                    message += '{}.'.format(die_roll)
                else:
                    message += 'and a {}.'.format(die_roll)

                if bonus_points:
                    pip_sum += bonus_points

                    if bonus_points > 0:
                        message += ' +{}'.format(bonus_points)
                    else:
                        message += ' {}'.format(bonus_points)

                message += '\n'
            elif i == quantity - 2:
                message += '{} '.format(die_roll)
            else:
                message += '{}, '.format(die_roll)

            pip_sum += die_roll

    message += 'For a total of **{}.**'.format(pip_sum)

    await ctx.send(message)


@bot.command(name='convert', aliases=['conv', 'cv'])
async def unit_convert(ctx, *, units):
    """Convert units"""

    unit_matches = []
    i = 0
    while i < len(units):
        ftin_match = SPECIAL_UNIT_PATTERN_TUPLE[1].match(units, i)
        if ftin_match:
            unit_matches.append((SPECIAL_UNIT_PATTERN_TUPLE[0], float(ftin_match.group(1)), float(ftin_match.group(2))))
            # unit_matches.append((unit_name, value in feet, value in inches))
            i = ftin_match.end()
            continue

        num_match = NUMBER_PATTERN.match(units, i)
        if num_match:
            i = num_match.end()
            def match(u): return (u[0], u[1].match(units, i))
            def falsey(x): return not x[1]
            unit = next(itertools.dropwhile(falsey, map(match, iter(UNIT_PATTERN_TUPLE))), None)
            if unit:
                (unit, unit_match) = unit
                unit_matches.append((unit, float(num_match.group(1))))
                i = unit_match.end()

        i += 1

    if unit_matches:
        await koabot.converter.convert_units(ctx, unit_matches)


@bot.command(name='exchange', aliases=['currency', 'xc', 'c'])
async def convert_currency(ctx, amount, currency_type1, _, currency_type2):
    """Convert currency to others"""

    currency_type1 = currency_type1.upper()
    currency_type2 = currency_type2.upper()
    converted_amount = bot.currency.convert(currency_type1, currency_type2, float(amount))

    await ctx.send('```%s %s → %0.2f %s```' % (amount, currency_type1, converted_amount, currency_type2))


@bot.command(name='4chan', aliases=['4c', '4ch'])
async def get_4chan_picture(ctx, user_board='u', thread_id=''):
    """Get a random picture from a specific board"""

    board = basc_py4chan.Board(user_board, https=True)
    if thread_id and re.findall(r'([0-9]+)', thread_id):
        thread = board.get_thread(int(thread_id))
        max_posts = 5

        if not thread:
            await ctx.send(random.choice(bot.quotes['thread_missing']))
            return

        posts_ready = []
        for post in thread.posts:
            embed = discord.Embed()

            if len(posts_ready) == 0:
                if thread.topic.subject:
                    embed.title = html.unescape(thread.topic.subject)
                else:
                    embed.title = '/%s/ thread' % user_board
                embed.url = thread.topic.url

            embed.set_author(
                name='%s @ %s' % (post.name, post.datetime),
                url=post.semantic_url)
            embed.add_field(name='No.%s' % post.post_id, value='\u200b')
            embed.description = post.text_comment

            if post.has_file:
                embed.set_image(url=post.file_url)

            posts_ready.append(embed)

            if len(posts_ready) >= max_posts:
                break

        if len(posts_ready) > 0:
            posts_ready[len(posts_ready) - 1].set_footer(
                text=bot.assets['4chan']['name'],
                icon_url=bot.assets['4chan']['favicon'])

        for post in posts_ready:
            await ctx.send(embed=post)
    else:
        threads = board.get_threads()
        max_threads = 2
        max_posts_per_thread = 2

        threads_ready = []
        for thread in threads:
            if thread.sticky:
                continue

            posts_ready = []
            fallback_post = None
            for post in thread.posts:
                if post.has_file:
                    embed = discord.Embed()

                    if len(posts_ready) == 0:
                        if thread.topic.subject:
                            embed.title = html.unescape(thread.topic.subject)
                        else:
                            embed.title = '/%s/ thread' % user_board

                        embed.url = thread.topic.url

                    embed.set_author(
                        name='%s @ %s' % (post.name, post.datetime),
                        url=post.semantic_url)
                    embed.add_field(name='No.%s' % post.post_id, value='\u200b')
                    embed.description = post.text_comment
                    embed.set_image(url=post.file_url)
                    posts_ready.append(embed)

                    if len(posts_ready) >= max_posts_per_thread:
                        break
                elif not fallback_post:
                    fallback_post = post

            if len(posts_ready) > 0:
                if len(posts_ready) < max_posts_per_thread and fallback_post:
                    embed = discord.Embed()
                    embed.set_author(
                        name='%s @ %s' % (fallback_post.name, fallback_post.datetime),
                        url=fallback_post.semantic_url)
                    embed.add_field(name='No.%s' % fallback_post.post_id, value='\u200b')
                    embed.description = fallback_post.text_comment
                    posts_ready.append(embed)

                posts_ready[len(posts_ready) - 1].set_footer(
                    text=bot.assets['4chan']['name'],
                    icon_url=bot.assets['4chan']['favicon'])
                threads_ready.append(posts_ready)

            if len(threads_ready) >= max_threads:
                break

        for post in list(itertools.chain.from_iterable(threads_ready)):
            if post.image.url:
                print(post.author.url + '\n' + post.image.url + '\n\n')
            else:
                print(post.author.url + '\nNo image\n\n')

            await ctx.send(embed=post)


def list_contains(lst, items_to_be_matched):
    """Helper function for checking if a list contains any elements of another list"""
    for item in items_to_be_matched:
        if item in lst:
            return True

    return False


@bot.command(aliases=['ava'])
async def avatar(ctx):
    """Display the avatar of an user"""

    if ctx.message.mentions:
        for mention in ctx.message.mentions:
            embed = discord.Embed()
            embed.set_image(url=mention.avatar_url)
            embed.set_author(
                name='%s #%i' % (mention.name, int(mention.discriminator)),
                icon_url=mention.avatar_url)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed()
        embed.set_image(url=ctx.message.author.avatar_url)
        embed.set_author(
            name='%s #%i' % (ctx.message.author.name, int(ctx.message.author.discriminator)),
            icon_url=ctx.message.author.avatar_url)
        await ctx.send(embed=embed)


def transition_old_config():
    """Transition any existing config folders to $XDG_CONFIG_HOME/BOT_DIRNAME"""
    old_config = os.path.join(SOURCE_DIR, 'config')

    if os.path.exists(old_config) and os.path.isdir(old_config):
        if len(os.listdir(old_config)) == 0:
            os.rmdir(old_config)
            print('Obsolete config folder deleted.')
        else:
            old_config_contents = glob.glob('{}/*'.format(old_config))
            for file_path in old_config_contents:
                filename = os.path.basename(file_path)

                if os.path.exists(os.path.join(CONFIG_DIR, filename)):
                    if os.path.samefile(file_path, os.path.join(CONFIG_DIR, filename)):
                        print('Files are the same!')
                        continue

                    os.remove(os.path.join(CONFIG_DIR, filename))

                print('Moving %s to %s...' % (filename, CONFIG_DIR))
                shutil.move(file_path, CONFIG_DIR)

            os.rmdir(old_config)
            print('The contents of config have been moved to %s.' % CONFIG_DIR)
    else:
        print('No config files were moved.')


def run_periodic_tasks():
    """Bot routines"""
    bot.loop.create_task(koabot.tasks.check_live_streamers())
    bot.loop.create_task(koabot.tasks.change_presence_periodically())


def load_all_extensions(path: str):
    """Recursively load all cogs in the project"""
    print('Loading cogs in project...')

    cog_prefix = 'koabot.cogs'
    cog_list = []

    for p, _, f in os.walk(path):
        for file in f:
            if file.endswith('.py'):
                container_dir = p.replace(path, '').replace('/', '.')
                (filename, _) = os.path.splitext(file)
                cog_path = cog_prefix + container_dir + '.' + filename
                cog_list.append(cog_path)

    for ext in cog_list:
        bot.load_extension(ext)
        print('Loaded "%s".' % ext)

    print('Finished loading cogs.')


@bot.check
async def beta_check(ctx):
    """Disable live instance if a beta instance is running"""
    beta_bot_id = bot.koa['discord_user']['beta_id']
    beta_bot = ctx.guild.get_member(beta_bot_id)

    if beta_bot and beta_bot.status == discord.Status.online:
        return ctx.guild.me.id == beta_bot_id
    return True


def start(debugging=False):
    """Start bot"""
    print('Initiating configuration...')

    # Move old config automatically to ~/.config/koa-bot
    transition_old_config()

    if debugging:
        print('In debug mode.')
        config_file = 'beta.jsonc'
    else:
        config_file = 'config.jsonc'

    config_paths = [os.path.join(CONFIG_DIR, config_file), os.path.join(CONFIG_DIR, 'auth.jsonc')]

    bot_data = {}
    for config_path in config_paths:
        with open(config_path) as json_file:
            bot_data.update(commentjson.load(json_file))

    bot.launch_time = datetime.utcnow()
    bot.__dict__.update(bot_data)

    twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'], bot.auth_keys['twitter']['consumer_secret'])
    twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
    bot.twitter_api = tweepy.API(twit_auth, wait_on_rate_limit=True)

    bot.pixiv_api = pixivpy3.AppPixivAPI()

    bot.danbooru_auth = aiohttp.BasicAuth(login=bot.auth_keys['danbooru']['username'], password=bot.auth_keys['danbooru']['key'])
    bot.e621_auth = aiohttp.BasicAuth(login=bot.auth_keys['e621']['username'], password=bot.auth_keys['e621']['key'])

    try:
        bot.mariadb_connection = mariadb.connect(host=bot.database['host'], user=bot.database['username'], password=bot.database['password'])
    except (mariadb.InterfaceError, mariadb.DatabaseError):
        print('Could not connect to the database! Functionality will be limited.')

    bot.currency = currency.CurrencyRates()

    run_periodic_tasks()
    load_all_extensions(os.path.join(SOURCE_DIR, 'cogs'))

    bot.run(bot.koa['token'])
