"""__main__.py"""
from sys import argv

import koabot.koakuma

if __name__ == '__main__':
    try:
        koabot.koakuma.start(argv[1] == '--debug')
    except IndexError:
        koabot.koakuma.start()
