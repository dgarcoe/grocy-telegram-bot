from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from config import Config

class Bot:

    def __init__(self, config: Config):

        self._config = config

        self._updater = Updater(self._config.TELEGRAM_BOT_TOKEN.value)
        self._dispatcher = self._updater.dispatcher

        self._dispatcher.add_handler(CommandHandler("start", self.start_command))
        self._dispatcher.add_handler(CommandHandler("help", self.help_command))

    def start(self):

        self._updater.start_polling()

        self._updater.idle()

    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!',
            reply_markup=ForceReply(selective=True),
        )


    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /help is issued."""
        update.message.reply_text('Help!')
