# Koakuma bot

### A Koakuma bot for our server!

![Koakuma](koabot/assets/avatar.png)

*"Eager to serve the sleepy."*

**Features:**

+ Selectively show missing link previews and related pictures from image links, based on channel safety.
    + Pixiv, Twitter, DeviantArt, among other image boards are supported.
    + Also get previews from stream services that lack one in their embed.
+ Be notified when select Twitch streamers go online.
+ Notifies users to move to a different channel upon breaking a condition.
    + Currently it's based on sending too many messages instead of links and videos.
+ Look up dictionary definitions in English and Japanese.
    + The alternative dictionary Urban Dictionary is supported too.
+ Easily move between channels by linking them together.
    + Referencing a text channel makes two links appear which lead to each other.
+ Get images by searching directly on image boards.
+ View your or other user's avatars.
+ Convert units from SI to Imperial.
    + Automatic conversion in messages is available, but prone to false positives.
+ Periodically does assigned tasks.
+ Plays music from local sources and from YouTube.
+ Roll the dice, for any amount and any number of pips per die.
+ Browse and look up forums in detail.
+ Convert your money currency to others *(i.e. USD → JPY)*.

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
The bot should automatically start on boot. You can manually run it by using the ``run.sh`` script on Linux, and ``winrun.bat`` on Windows.
