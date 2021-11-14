import logging

from container_app_conf import ConfigBase
from container_app_conf.entry.string import StringConfigEntry
from container_app_conf.entry.int import IntConfigEntry
from container_app_conf.entry.list import ListConfigEntry
from container_app_conf.source.yaml_source import YamlSource

ROOT = "grocy-telegram-bot"

TELEGRAM = "telegram"

GROCY = "grocy"

class Config(ConfigBase):

    def __new__(cls, *args, **kwargs):
        yaml_source = YamlSource(ROOT, path=["./config"])
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

    TELEGRAM_USER_IDS = ListConfigEntry(
        item_type=IntConfigEntry,
        key_path=[
            ROOT,
            TELEGRAM,
            "user_ids"
        ],
        required=True,
        example=[
            123456789,
            987654321
        ]
    )

    GROCY_API_KEY = StringConfigEntry(
        description = "API key used to communicate with Grocy",
        example = "abcdefgh12345678",
        secret = True,
        required = True,
        key_path = [
            ROOT,
            GROCY,
            "api_key"
        ]
    )

    GROCY_HOST = StringConfigEntry(
        description = "URL to the Grocy host (port not included)",
        example = "http://127.0.0.1",
        required = True,
        key_path = [
            ROOT,
            GROCY,
            "host"
        ]
    )

    GROCY_PORT = IntConfigEntry(
        description = "Grocy port",
        example = 80,
        required = True,
        key_path = [
            ROOT,
            GROCY,
            "port"
        ]
    )
