"""__main__.py"""
from sys import argv

if __name__ == '__main__':
    from koabot import koakuma
    try:
        koakuma.start(argv[1] == '--debug')
    except IndexError:
        koakuma.start()
