import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from emoji import emojize
from functools import wraps

from .config import Config
from .grocy import Grocy
from .commands.shopping_list import ShoppingListCommandHandler
from .commands.house_chores import HouseChoresCommandHandler


class Bot:

    def __init__(self, config: Config, grocy: Grocy):

        self._config = config
        self._grocy = grocy
        self._shopping_list_command_handler = ShoppingListCommandHandler(self._config, self._grocy)
        self._house_chores_command_handler = HouseChoresCommandHandler(self._config, self._grocy)

        self._updater = Updater(self._config.TELEGRAM_BOT_TOKEN.value)
        self._dispatcher = self._updater.dispatcher

        self._dispatcher.add_handler(CommandHandler("start", self.start_command))
        self._dispatcher.add_handler(CommandHandler("help", self.help_command))
        self._dispatcher.add_handler(CommandHandler("menu", self.menu_command))

        for handler in self._shopping_list_command_handler.handlers():
            self._dispatcher.add_handler(handler)

        for handler in self._house_chores_command_handler.handlers():
            self._dispatcher.add_handler(handler)

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def start(self):

        self._updater.start_polling()

        self._updater.idle()

    def restricted(func):
        @wraps(func)
        def wrapped(self,update, context, *args, **kwargs):
            user_id = update.effective_user.id
            if user_id not in self._config.TELEGRAM_USER_IDS.value:
                print("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self, update, context, *args, **kwargs)
        return wrapped

    @restricted
    def start_command(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\! Welcome to Grocy Telegram Bot\. Please use the /help command to check'
            fr' all the available options\.'
        )

    @restricted
    def help_command(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text('List of commands:\n'
                                  '/menu: Show the main menu with all the available options.\n\n'
                                  'List of options in main menu:\n'
                                  '-Shopping List: Shows the shopping list.\n '
                                  '\t*Use the plus button to add a new item as "quantity item". Eg. 2 bottles.\n'
                                  '\t*Use the check button to check items from the list.\n'
                                  '\t*Delete the whole list by pressing the basket button.')

    @restricted
    def menu_command(self, update: Update, context: CallbackContext) -> None:
        """Sends a message with three inline buttons attached."""
        keyboard = [
            [InlineKeyboardButton(emojize(":shopping_cart: Shopping List"), callback_data='shopping')],
            [InlineKeyboardButton(emojize(":broom: House Chores"), callback_data='chores')]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose an option:', reply_markup=reply_markup)
