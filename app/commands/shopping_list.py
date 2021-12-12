import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters
from emoji import emojize

from . import GrocyCommandHandler

class ShoppingListCommandHandler(GrocyCommandHandler):

    ADD_SHOPPING_ITEMS = range(1)
    shopping_list = []

    def handlers(self):
        return [
            CallbackQueryHandler(self.shopping, pattern='^shopping$'),
            CallbackQueryHandler(self.delete_shopping, pattern='^delete_shopping$'),
            CallbackQueryHandler(self.delete_shopping_yes, pattern='^delete_shopping_yes$'),
            CallbackQueryHandler(self.check_shopping, pattern='^check_shopping$'),
            CallbackQueryHandler(self.check_shopping_item, pattern='^check_shopping_item:\d+:\d+$'),
            ConversationHandler(
                entry_points=[CallbackQueryHandler(self.add_shopping, pattern='^add_shopping$')],
                states={
                    self.ADD_SHOPPING_ITEMS: [MessageHandler(Filters.text & ~Filters.command, self.add_shopping_item)]
                },
                fallbacks=[MessageHandler(Filters.command, self.cancel_add_shopping_item)],
                allow_reentry=True
            )
        ]

    def shopping(self, update: Update, context: CallbackContext) :

        query = update.callback_query
        query.answer()

        query.edit_message_text(
            text="Please wait while getting items...")

        self.shopping_list = self._grocy.get_shopping_list()

        response = [emojize(":shopping_cart: Shopping List\n\n")]
        for item in self.shopping_list:
            item_description = self.strike("- {}x {}".format(item.amount, item.product_name))+"\n" if item.done else \
                "- {}x {}\n".format(item.amount,item.product_name)
            response.append(item_description)

        if not self.shopping_list :
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
        if re.match(r"^([0-9]+ [ a-zA-ZÀ-ÿ]+)$", items):
            params = items.split(" ", 1)
            amount = int(params[0])
            item_name = params[1]

            to_add = {"amount":amount,"note":item_name}

            self._grocy.add_item_shopping_list(to_add)

            update.message.reply_text('Thank you! {}x of {} added!'.format(amount, item_name),reply_markup=reply_markup)
        else:
            update.message.reply_text('Format error in item description. Please try again.', reply_markup=reply_markup)

        return ConversationHandler.END

    def cancel_add_shopping_item(self, update: Update, context: CallbackContext):
        return ConversationHandler.END

    def check_shopping(self, update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        keyboard = []

        message = "Check items from the list:"
        counter = 0
        for index, item in enumerate(self.shopping_list):
            if not item.done:
                button = [InlineKeyboardButton(item.product_name, callback_data='check_shopping_item:{}:{}'.format(index,item.id))]
                keyboard.append(button)
                counter += 1

        if not counter:
            message = "No items to check"

        keyboard.append([InlineKeyboardButton("Back", callback_data='shopping')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=message, reply_markup=reply_markup)

    def check_shopping_item(self, update: Update, context: CallbackContext):

        query = update.callback_query
        query.answer()

        keyboard = []
        keyboard.append([InlineKeyboardButton("Back", callback_data='check_shopping')])

        item_index = update.callback_query.data.split(":")[1]
        item_id = update.callback_query.data.split(":")[2]
        self.shopping_list[int(item_index)].done = True
        self._grocy.mark_item_done_shopping_list(item_id)

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text="Item checked!", reply_markup=reply_markup)

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

    def strike(self, text):
        return emojize(":check_mark_button:")+text.replace("-","")