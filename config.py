import logging

from container_app_conf import ConfigBase
from container_app_conf.entry.string import StringConfigEntry
from container_app_conf.source.yaml_source import YamlSource

ROOT = "grocy-telegram-bot"

TELEGRAM = "telegram"

class Config(ConfigBase):

    def __new__(cls, *args, **kwargs):
        yaml_source = YamlSource(ROOT)
        data_sources = [
            yaml_source
        ]
        return super(Config, cls).__new__(cls, data_sources=data_sources)

    TELEGRAM_BOT_TOKEN = StringConfigEntry(
        description = "Telegram Bot token used to authenticate with Telegram's API",
        example = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        secret = True,
        required = True,
        key_path = [
            ROOT,
            TELEGRAM,
            "token"
        ]
    )
