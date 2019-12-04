# Koa bot
### A Koakuma bot for our server!

![Koakuma](avatar.png)

Eager to serve the sleepy.

**Features:**
+ Display missing link previews and albums from image links, based on channel type.
    + Pixiv, Twitter, Deviantart, among other image boards are supported.
    + Also get previews from streams that lack a preview.
+ Keep track of the status of select Twitch streamers.
+ Reminds you to move to a different channel.
+ Look up dictionary definitions in English and Japanese.
+ View post results searching directly from image boards.
+ Get unit conversions on the fly.
+ Periodically does assigned tasks.


## How to setup
1. Install python 3.5.3. If you are on Linux and stuck on a higher version try with ``pyenv``. This version is required because Raspbian has that version in their repository.
2. If you already have the python3 ``virtualenv``, run ``virtualenv -p python venv``. This assumes that you are running this command while on python 3.5.3.
3. From within the virtual environment install the requirements.
```bash
source venv/bin/activate
python -V # making sure it prints version 3.5.3
pip install -r requirements.txt
```
4. It's done. Now run the bot from within the venv.
