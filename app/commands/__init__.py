
from app.config import Config
from app.grocy import Grocy

class GrocyCommandHandler:

    def __init__(self, config: Config, grocy: Grocy):
        self._config = config
        self._grocy = grocy
