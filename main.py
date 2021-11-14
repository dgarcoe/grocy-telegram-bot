import logging

from app.config import Config
from app.bot import Bot
from app.grocy import Grocy

import requests

def main():

    config = Config()

    grocy = Grocy(config)

    bot = Bot(config, grocy)
    bot.start()


if __name__ == '__main__':
    main()
