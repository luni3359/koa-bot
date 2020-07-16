# Koakuma bot

### A Discord bot for our server!

![Koakuma](koabot/assets/avatar.png)

*"Eager to serve the sleepy."*

## Features

### Images
+ Display previews from galleries or from related images.
    + Supported: danbooru, e621, imgur, pixiv, twitter

+ Show missing link previews from image links.
    + Supported: danbooru, deviantart, e621, pixiv, sankaku

+ View your avatar, or your friend's by pinging them.
+ Get images by searching directly on image boards.
    + Supported: danbooru, e621


These functions factor in the safety setting a channel is set to, like not displaying nsfw missing previews in sfw channels or ignoring nsfw entries from galleries when posted in sfw channels. However, some services make it impossible to tell their rating apart reliably. By default the bot leans toward being non-restrictive, so services like imgur and twitter don't respect this feature.

### Streams
+ Get notifications when select Twitch streamers go online.
+ See static previews from streaming services that lack one in their embed.
    + Supported: picarto

### Forums
+ Browse and look up forums in detail.
    + Currently only 🍀 is supported, but there's plans for 👽.

### Games
+ Roll the dice, as many as you want, of any number of pips.
    + You can mix up rolls however you want (e.g. ``!roll d6 2d2``)

### Music
+ Play music from local sources and from YouTube.

### Moderation
+ Notifies users to move to a different channel upon breaking a condition.
    + Currently it's based on sending too many messages instead of links and videos.
+ Easily move between channels by linking them together.
    + Referencing a text channel makes two links appear which lead to each other.

### Miscellanous
+ Look up dictionary definitions in English and Japanese.
    + The alternative dictionary Urban Dictionary is supported too.
+ Get short summaries from articles right from Wikipedia.
+ Convert units from SI to Imperial.
    + Automatic conversion in messages is available as a setting, but prone to false positives.
+ Convert your money currency to others *(e.g. USD → JPY)*.
+ View the time around the world.
+ Periodically does assigned tasks.


## About
Discord lacks some features we deem important that were neglected as bots rose in popularity (and for good reason, they're just too useful).

This bot was born to solve the need to view Twitter previews, as in the past they used to show only the first picturUserActions:
e in a tweet, skipping the rest.

Today Twitter previews were partially fixed by Discord, but they are inconsistent between mobile and desktop, and the thumbnails they show are cropped.


## How to setup
1. Install python 3.7.3.
    + This version is required because Raspbian has that version in their repository. If you are on Linux and on a different version try with ``pyenv``.
2. If you already have the python3 ``virtualenv`` binary, run ``virtualenv -p python nameofyourvenv``. This assumes that you are running this command while on python 3.7.3.
3. From within the virtual environment install the requirements.
```bash
# in koa-bot...
source venv/bin/activate
python -V # making sure it prints version 3.7.3
pip install -r requirements.txt
```
4. It's done. Now run the bot from within the venv.

## How to run
Once installed, this bot should automatically start on the next reboot. You can manually run it by using the ``run.sh`` script on Linux, and ``winrun.bat`` on Windows.
