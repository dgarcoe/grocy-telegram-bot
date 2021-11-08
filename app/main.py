import logging

from config import Config
from bot import Bot
from grocy import Grocy

import requests

def main():

    config = Config()

    grocy = Grocy(config)

    bot = Bot(config, grocy)
    bot.start()


if __name__ == '__main__':
    main()
