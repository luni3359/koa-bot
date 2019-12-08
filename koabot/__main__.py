from sys import argv

if __name__ == '__main__':
    from koabot import koakuma
    koakuma.start(argv[1] == '--debug')
