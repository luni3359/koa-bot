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
3. You're done!

You might need to install additional dependencies either via pip or through your package manager to make use of ImageHash. If you have problems getting the right Python version check out [pyenv](https://github.com/pyenv/pyenv).

## How to run

You can manually run the bot by executing the `run.sh` script on Linux, and `winrun.cmd` on Windows.
