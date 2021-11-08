import logging

from telegram import Update, ForceReply,  InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from emoji import emojize
from functools import wraps

from config import Config
from grocy import Grocy

class Bot:

    def __init__(self, config: Config, grocy: Grocy):

        self._config = config
        self._grocy = grocy

        self._updater = Updater(self._config.TELEGRAM_BOT_TOKEN.value)
        self._dispatcher = self._updater.dispatcher

        self._dispatcher.add_handler(CommandHandler("start", self.start_command))
        self._dispatcher.add_handler(CommandHandler("help", self.help_command))
        self._dispatcher.add_handler(CallbackQueryHandler(self.shopping,pattern='^shopping$'))
        self._dispatcher.add_handler(CommandHandler("menu", self.menu_command))

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

    def restricted(func):
        @wraps(func)
        def wrapped(self,update, context, *args, **kwargs):
            user_id = update.effective_user.id
            if user_id not in self._config.TELEGRAM_USER_IDS.value:
                print("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self,update, context, *args, **kwargs)
        return wrapped

    def start(self):

        self._updater.start_polling()

        self._updater.idle()

    @restricted
    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!'
        )

    @restricted
    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /help is issued."""
        update.message.reply_text('Help!')

    @restricted
    def shopping(self, update: Update, context: CallbackContext) -> int:
        """Show new choice of buttons"""
        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="Please wait while getting items...")

        shopping_list = self._grocy.get_shopping_list()

        response = [emojize(":shopping_cart: Shopping List\n\n")]
        for item in shopping_list:
            response.append("- {}x {}\n".format(item.amount,item.product_name))

        response_text = ''.join(response)

        query.edit_message_text(
            text=response_text)

    @restricted
    def menu_command(self, update: Update, context: CallbackContext) -> None:
        """Sends a message with three inline buttons attached."""
        keyboard = [
            [InlineKeyboardButton(emojize(":shopping_cart: Shopping List"), callback_data='shopping')]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose an option:', reply_markup=reply_markup)
