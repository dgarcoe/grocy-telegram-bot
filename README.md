# Grocy Telegram Bot
A Telegram bot to communicate with your Grocy instance!

## Description
This Telegram bot is my own implementation based on the original [Grocy Telegram Bot](https://github.com/markusressel/grocy-telegram-bot).

At the moment only the shopping list feature is completed and implemented. Many more will come!

## Dependencies
* requests
* python-telegram-bot
* container_app_conf
* pydantic
* emoji

## Configuration file
Before running the bot a configuration file must be created. This file follows the YAML format and can be placed in the folder where you run the docker-compose file (see next section).

The following is an example of a configuration file that you should edit with your own parameters:

```
grocy-telegram-bot:
  telegram:
    token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_ids:
      - 111111111
      - 2222222222
  grocy:
    api_key: "abcdefgh12345678"
    host: "http://192.168.1.100"
    port: 9283
```

## Running the bot
You can use the docker-compose file provided in the repo and simply run the following:
`docker-compose up -d`
