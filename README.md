# Koakuma bot

### A Discord bot for our server!

![Koakuma](koabot/assets/avatar.png)  
*"Eager to serve the sleepy."*

## Features

### Rich embeds

Top websites will have their embeds overriden by me! Be it a lacking embed, or one that's been purposefully gimped.

+ Automatically get better embed previews of the link you're sharing with your friends.
  + Supported sites: danbooru, e621, imgur, pixiv, twitter, reddit

### Search anime images

Got tired of uploading entire images or posting multiple links to see the previews of that very short comic you want others to see? Don't worry, we got you covered!

+ Search tags directly from anime picture boards!
  + Supported sites: danbooru, e621
+ Paired with rich embeds, expect your links to show more bang for the paste!

By default some restrictions will apply based on the safety setting your text channel is set to, such as to avoid embarrassing situations, but you can configure it to behave in any way you like. However, some sites make it impossible to tell apart the safety rating of their images, so sites like imgur and twitter ignore this check entirely.

### Keep track of your streamers

+ Get notifications when your favorite streamers go online.
  + Supported sites: twitch
+ See a small image preview of the stream links that lack one, like Picarto's.

### Game features

+ Roll the dice, as many as you want, of any number of pips!
  + You can mix up rolls however you want (e.g. `!roll d6 2d2`)

### Play music

+ Play music from local sources and from YouTube.

### Moderation

+ Notifies users to move to a different channel upon breaking a condition.
  + Currently it's based on sending too many messages in channels based around media.
+ Easily move between channels by linking them together.
  + Starting a message with `!` will link the current channel to all channel mentions between each other.
+ Let users get roles based on reactions

### Miscellaneous

+ View your avatar, or your friend's by pinging them.
+ Look up dictionary definitions in English and Japanese.
  + The alternative dictionary Urban Dictionary is supported too.
+ Get short summaries from articles right from Wikipedia.
+ Convert units from SI to Imperial.
  + Automatic conversion after messages are sent is available as a setting.
+ Convert your money currency to others *(e.g. USD → JPY)*.
+ View the time around the world.
+ Browse and look up forums in detail.
  + Currently only 🍀 is supported, but there's plans for 👽.
+ Periodically does assigned tasks.

## About

Discord lacks a lot of features that they don't seem to care about to implement, so this bot was born to satisfy our needs.

For example, at first Twitter previews used to show only one image regardless of how many a tweet had. Now a days they work on desktop, but in my opinion they suck since they're poorly cropped, trying to fit into one small embed. They also look differently between mobile and desktop, retaining their old behavior on the former.

## How to setup

1. Make sure you've got python 3.8 or above installed.
2. Install the dependencies from `requirements.txt`.
3. Create a file named `auth.jsonc` under `~/.config/koa-bot` and fill in your secrets as shown below. Replace `site_name` with the name of the website you want the bot to authenticate with, `token_name` with the name of the field (i.e. `token`), and put your secret as the `token_value`.

```jsonc
{
    "auth_keys": {
      "site_name": {
        "token_name": "token_value"
      }
    }
}
```

You might need to install additional dependencies either via pip or through your package manager to make use of ImageHash. If you have problems getting the right Python version check out [pyenv](https://github.com/pyenv/pyenv).

## How to run

You can manually run the bot by executing the `run.sh` script on Linux, and `winrun.cmd` on Windows.

```text
$ $KOAKUMA_HOME/run.sh
Initiating...
```

## How to update

The bot features an easy-to-use local update function in its run scripts for those times you're debugging and aren't sure whether it's a good idea to commit anything yet.

### Updating only to the host

You can use the `-u` flag to send all development changes you've made to your server, but you will first need to define the environmental variable `KOAKUMA_CONNSTR` *locally* and then define `KOAKUMA_HOME` in your *server*.

You can define these variables anywhere within your system, but it's preferable if you place them within a `.env` file that should be located inside the bot's folder. The run script will read off of this file if it exists.

```text
$ $KOAKUMA_HOME/run.sh -u
Updating bot files...
Exporting dependencies to requirements.txt...
Transferring source from /home/user/koa-bot to remoteuser@192.168.1.2:/home/remoteuser/koa-bot
sending incremental file list
README.md
          4,731 100%    3.84MB/s    0:00:00 (xfr#1, to-chk=75/78)
requirements.txt
          3,614 100%    3.45MB/s    0:00:00 (xfr#2, to-chk=70/78)

sent 3,260 bytes  received 146 bytes  57.24 bytes/sec
total size is 11,518,109  speedup is 3,381.71

Transferring config files from /home/user/.config/koa-bot/ to remoteuser@192.168.1.2:~/.config/koa-bot
sending incremental file list

sent 256 bytes  received 12 bytes  178.67 bytes/sec
total size is 58,011  speedup is 216.46
Update complete!
```
