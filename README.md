# Koa bot
### A Koakuma bot for our server!

![Koakuma](koabot/assets/avatar.png)

*Eager to serve the sleepy.*

**Features:**
+ Display missing link previews and albums from image links, based on channel type.
    + Pixiv, Twitter, DeviantArt, among other image boards are supported.
    + Also get previews from streams that lack one.
+ Be notified when select Twitch streamers go online.
+ Reminds you to move to a different channel.
+ Look up dictionary definitions in English and Japanese.
    + The alternative dictionary Urban Dictionary is supported.
+ Easily move between channels by linking them together.
    + Referencing a text channel makes two links appear which lead to each other.
+ Show post results searching directly from image boards.
+ View user avatars.
+ Get unit conversions ~~on the fly~~ on demand.
    + Automatic conversion will move from being default to optional.
+ Periodically does assigned tasks.
+ Plays music.
+ Roll the dice, for any amount and any number of pips.
+ Browse and look up forums in detail.
+ Convert your money currency to others *(i.e. USD → JPY)*

## How to setup
1. Install python 3.7.3.
    + This version is required because Raspbian has that version in their repository. If you are on Linux and stuck on a higher version try with ``pyenv``.
2. If you already have the python3 ``virtualenv``, run ``virtualenv -p python venv``. This assumes that you are running this command while on python 3.7.3.
3. From within the virtual environment install the requirements.
```bash
# in koa-bot...
source venv/bin/activate
python -V # making sure it prints version 3.7.3
pip install -r requirements.txt
```
4. It's done. Now run the bot from within the venv.
