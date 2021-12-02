from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters
from emoji import emojize

from . import GrocyCommandHandler

class HouseChoresCommandHandler(GrocyCommandHandler):

    house_chores_list = []

    def handlers(self):
        return [
            CallbackQueryHandler(self.chores, pattern='^chores$'),
        ]

    def chores(self,update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="Please wait while getting chores...")

        self.house_chores_list = self._grocy.get_chores_list()

        response = [emojize(":broom: House Chores\n\n")]
        for chore in self.house_chores_list:
            response.append("- "+chore.chore_name+'\n')

        if not self.house_chores_list:
            response.append("No chores configured\n")

        response_text = ''.join(response)

        keyboard = [
            [InlineKeyboardButton(emojize(":check_mark_button:"), callback_data='check_chores')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=response_text, reply_markup=reply_markup)
