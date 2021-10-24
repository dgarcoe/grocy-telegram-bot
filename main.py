import logging

from config import Config
from bot import Bot

def main():

    config = Config()

    bot = Bot(config)
    bot.start()


if __name__ == '__main__':
    main()
