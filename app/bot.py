import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, Filters
from emoji import emojize
from functools import wraps

from .config import Config
from .grocy import Grocy
from .commands.shopping_list import ShoppingListCommandHandler

class Bot:

    def __init__(self, config: Config, grocy: Grocy):

        self._config = config
        self._grocy = grocy
        self._shopping_list_command_handler = ShoppingListCommandHandler(self._config, self._grocy)

        self._updater = Updater(self._config.TELEGRAM_BOT_TOKEN.value)
        self._dispatcher = self._updater.dispatcher

        self._dispatcher.add_handler(CommandHandler("start", self.start_command))
        self._dispatcher.add_handler(CommandHandler("help", self.help_command))
        self._dispatcher.add_handler(CallbackQueryHandler(self._shopping_list_command_handler.shopping, pattern='^shopping$'))
        self._dispatcher.add_handler(CallbackQueryHandler(self._shopping_list_command_handler.delete_shopping,
                                                          pattern='^delete_shopping$'))
        self._dispatcher.add_handler(CallbackQueryHandler(self._shopping_list_command_handler.delete_shopping_yes,
                                                          pattern='^delete_shopping_yes$'))
        self._dispatcher.add_handler(CommandHandler("menu", self.menu_command))

        add_shopping_list_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self._shopping_list_command_handler.add_shopping
                                               , pattern='^add_shopping$')],
            states={
                self._shopping_list_command_handler.ADD_SHOPPING_ITEMS : [MessageHandler(Filters.text & ~Filters.command,
                                                                                         self._shopping_list_command_handler.add_shopping_item)]
            },
            fallbacks=[CallbackQueryHandler(self._shopping_list_command_handler.shopping
                                            , pattern='^shopping$')]
        )
        self._dispatcher.add_handler(add_shopping_list_conv_handler)

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

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
            return func(self,update, context, *args, **kwargs)
        return wrapped

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
    def menu_command(self, update: Update, context: CallbackContext) -> None:
        """Sends a message with three inline buttons attached."""
        keyboard = [
            [InlineKeyboardButton(emojize(":shopping_cart: Shopping List"), callback_data='shopping')]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose an option:', reply_markup=reply_markup)
