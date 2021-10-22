"""__main__.py"""
from sys import argv

from koabot.koakuma import start

if __name__ == '__main__':
    start('--debug' in argv)
