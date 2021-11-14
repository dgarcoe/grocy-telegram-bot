import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from emoji import emojize

from . import GrocyCommandHandler

class ShoppingListCommandHandler(GrocyCommandHandler):

    ADD_SHOPPING_ITEMS = range(1)

    def shopping(self, update: Update, context: CallbackContext) -> int :
        """Show new choice of buttons"""
        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="Please wait while getting items...")

        shopping_list = self._grocy.get_shopping_list()

        response = [emojize(":shopping_cart: Shopping List\n\n")]
        for item in shopping_list:
            response.append("- {}x {}\n".format(item.amount,item.product_name))

        if not shopping_list :
            response.append("No items in shopping list\n")

        response_text = ''.join(response)

        keyboard = [
            [InlineKeyboardButton(emojize(":plus:"), callback_data='add_shopping'),
             InlineKeyboardButton(emojize(":check_mark_button:"), callback_data='check_shopping')],
            [InlineKeyboardButton(emojize(":wastebasket:"), callback_data='delete_shopping')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=response_text, reply_markup=reply_markup)

    def add_shopping(self, update: Update, context: CallbackContext) -> int:

        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="What do you want to add to the list?")

        return self.ADD_SHOPPING_ITEMS

    def add_shopping_item(self, update: Update, context: CallbackContext) -> int:

        items = update.message.text

        keyboard = [
            [InlineKeyboardButton("Back", callback_data='shopping')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # if we want to match a list of items use this ^([0-9]+ [a-zA-ZÀ-ÿ\u00f1\u00d1]+,?\s*)+$
        if re.match(r"^([0-9]+ [a-zA-ZÀ-ÿ]+)$", items):
            params = items.split()
            amount = int(params[0])
            item_name = params[1]

            to_add = {"amount":amount,"note":item_name}

            self._grocy.add_item_shopping_list(to_add)

            update.message.reply_text('Thank you! {}x of {} added!'.format(amount, item_name),reply_markup=reply_markup)
        else:
            update.message.reply_text('Format error in item description. Please try again.',reply_markup=reply_markup)

        return ConversationHandler.END

    def check_shopping(self, update: Update, context: CallbackContext):
        pass

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

    def delete_shopping_yes(self, update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        self._grocy.clear_shopping_list()

        query.edit_message_text(
            text="Shopping list cleared")