"""__main__.py"""
import os
from sys import argv

from koabot.koakuma import start

if os.name != "nt":
    import uvloop

    uvloop.install()

if __name__ == '__main__':
    start('--debug' in argv)
