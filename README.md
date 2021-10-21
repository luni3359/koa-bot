# Koakuma bot

### A Discord bot for our server!

![Koakuma](koabot/assets/avatar.png)

*"Eager to serve the sleepy."*

## Features

### Search anime images
Got tired of uploading entire images or posting multiple links to see the previews of that very short comic you want others to see? Don't worry, we got you covered!

+ Automatically get previews of the pictures related to the post you're sharing with your friends.
    + Supported sites: danbooru, e621, imgur, pixiv, twitter

+ Your link doesn't show a preview on Discord for arbitrary reasons? That won't stop me!
    + Supported sites: danbooru, deviantart, e621, pixiv, sankaku

+ Search tags directly from anime picture boards!
    + Supported sites: danbooru, e621

By default some restrictions will apply based on the safety setting your text channel is set to, such as to avoid embarrassing situations, but you can configure it to behave in any way you like. However, some sites make it impossible to tell apart the safety rating of their images, so sites like imgur and twitter ignore this check entirely.

### Keep track of your streamers
+ Get notifications when your favorite streamers go online.
    + Supported sites: twitch
+ See a small image preview of the stream links that lack one, like Picarto's.

### Game features
+ Roll the dice, as many as you want, of any number of pips!
    + You can mix up rolls however you want (e.g. ``!roll d6 2d2``)

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
Discord lacks a ton of features that they don't seem to care about to implement, so this bot was born to satisfy our needs.

For example, at first Twitter previews used to show only one image regardless of how many a tweet had. Now a days they work on desktop, but in my opinion they suck since they're poorly cropped, trying to fit into one small embed. They also look differently between mobile and desktop, retaining their old behavior on the former.


## How to setup
1. Install python 3.7.3 (current version on Raspberry Pi OS).
    + If you have problems switching versions try using ``pyenv``.
2. Install the dependencies from ``requirements.txt``.
> Note: You might need to install additional dependencies either via pip or through your package manager to make use of ImageHash.
3. You're done!

## How to run
Once installed, this bot should automatically start on the next reboot.

You can manually run it by executing the ``run.sh`` script on Linux, and ``winrun.cmd`` on Windows.
