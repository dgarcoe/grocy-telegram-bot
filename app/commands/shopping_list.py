from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from emoji import emojize

from .restricted import  restricted
from . import GrocyCommandHandler

class ShoppingListCommandHandler(GrocyCommandHandler):

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

        keyboard = [
            [InlineKeyboardButton(emojize(":wastebasket:"), callback_data='delete_shopping')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=response_text, reply_markup=reply_markup)

    @restricted
    def delete_shopping(self, update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        keyboard = [
            [InlineKeyboardButton("Yes", callback_data='delete_shopping_yes'),
             InlineKeyboardButton("No", callback_data='shopping')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text="Do you really want to clear the whole shopping list?", reply_markup=reply_markup)

    @restricted
    def delete_shopping_yes(self, update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="Shopping list cleared")