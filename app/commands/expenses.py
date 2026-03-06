from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)
from emoji import emojize

from app.config import Config
from app.expenses import ExpenseTracker

# Add Expense conversation states
(ASK_DESCRIPTION, ASK_AMOUNT, ASK_PAYER, ASK_PARTICIPANTS, CONFIRM_EXPENSE) = range(5)

# Settle Up conversation states
(SETTLE_ASK_PAYER, SETTLE_ASK_RECEIVER, SETTLE_ASK_AMOUNT, SETTLE_CONFIRM) = range(4)

# context.user_data keys
CONTEXT_DESCRIPTION  = "exp_description"
CONTEXT_AMOUNT       = "exp_amount"
CONTEXT_PAYER        = "exp_payer"
CONTEXT_PARTICIPANTS = "exp_participants"
CONTEXT_SETTLE_PAYER = "settle_payer"
CONTEXT_SETTLE_TO    = "settle_to"
CONTEXT_SETTLE_AMT   = "settle_amount"


class ExpensesCommandHandler:

    def __init__(self, config: Config, expense_tracker: ExpenseTracker):
        self._config = config
        self._tracker = expense_tracker

    @property
    def _members(self):
        return self._config.EXPENSES_MEMBERS.value or []

    def handlers(self):
        return [
            CallbackQueryHandler(self.expenses_menu, pattern='^expenses$'),
            CallbackQueryHandler(self.view_balances, pattern='^view_balances$'),

            ConversationHandler(
                entry_points=[CallbackQueryHandler(self.add_expense_start, pattern='^add_expense$')],
                states={
                    ASK_DESCRIPTION: [
                        MessageHandler(Filters.text & ~Filters.command, self.add_expense_description)
                    ],
                    ASK_AMOUNT: [
                        MessageHandler(Filters.text & ~Filters.command, self.add_expense_amount)
                    ],
                    ASK_PAYER: [
                        CallbackQueryHandler(self.add_expense_payer, pattern='^exp_payer:.+$')
                    ],
                    ASK_PARTICIPANTS: [
                        CallbackQueryHandler(self.add_expense_toggle_participant, pattern='^exp_toggle:.+$'),
                        CallbackQueryHandler(self.add_expense_participants_done, pattern='^exp_participants_done$'),
                    ],
                    CONFIRM_EXPENSE: [
                        CallbackQueryHandler(self.add_expense_confirm_yes, pattern='^exp_confirm_yes$'),
                        CallbackQueryHandler(self.add_expense_confirm_no, pattern='^exp_confirm_no$'),
                    ],
                },
                fallbacks=[MessageHandler(Filters.command, self.cancel_add_expense)],
                allow_reentry=True
            ),

            ConversationHandler(
                entry_points=[CallbackQueryHandler(self.settle_start, pattern='^settle_up$')],
                states={
                    SETTLE_ASK_PAYER: [
                        CallbackQueryHandler(self.settle_payer, pattern='^settle_payer:.+$')
                    ],
                    SETTLE_ASK_RECEIVER: [
                        CallbackQueryHandler(self.settle_receiver, pattern='^settle_to:.+$')
                    ],
                    SETTLE_ASK_AMOUNT: [
                        MessageHandler(Filters.text & ~Filters.command, self.settle_amount)
                    ],
                    SETTLE_CONFIRM: [
                        CallbackQueryHandler(self.settle_confirm_yes, pattern='^settle_confirm_yes$'),
                        CallbackQueryHandler(self.settle_confirm_no, pattern='^settle_confirm_no$'),
                    ],
                },
                fallbacks=[MessageHandler(Filters.command, self.cancel_settle)],
                allow_reentry=True
            ),
        ]

    # ── Expenses menu ─────────────────────────────────────────────────────────

    def expenses_menu(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        keyboard = [
            [InlineKeyboardButton(emojize(":bar_chart: View Balances"), callback_data='view_balances')],
            [InlineKeyboardButton(emojize(":plus: Add Expense"),        callback_data='add_expense')],
            [InlineKeyboardButton(emojize(":handshake: Settle Up"),     callback_data='settle_up')],
        ]
        query.edit_message_text(
            text=emojize(":money_bag: Expenses"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── View Balances ─────────────────────────────────────────────────────────

    def view_balances(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()

        balances = self._tracker.get_balances()

        if not balances:
            text = emojize(":check_mark_button: All settled up! No outstanding balances.")
        else:
            lines = [emojize(":bar_chart: Current Balances\n")]
            for debtor, creditor, amount in balances:
                lines.append(f"{debtor} owes {creditor} \u20ac{amount:.2f}")
            text = "\n".join(lines)

        keyboard = [[InlineKeyboardButton("Back", callback_data='expenses')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Add Expense ───────────────────────────────────────────────────────────

    def add_expense_start(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data.pop(CONTEXT_DESCRIPTION, None)
        context.user_data.pop(CONTEXT_AMOUNT, None)
        context.user_data.pop(CONTEXT_PAYER, None)
        context.user_data[CONTEXT_PARTICIPANTS] = set()

        if not self._members:
            keyboard = [[InlineKeyboardButton("Back", callback_data='expenses')]]
            query.edit_message_text(
                text="No members configured. Please add members to your config file.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END

        query.edit_message_text(text="What is the expense for? (e.g. Groceries, Dinner...)")
        return ASK_DESCRIPTION

    def add_expense_description(self, update: Update, context: CallbackContext) -> int:
        context.user_data[CONTEXT_DESCRIPTION] = update.message.text.strip()
        update.message.reply_text("How much did it cost? (e.g. 24.50)")
        return ASK_AMOUNT

    def add_expense_amount(self, update: Update, context: CallbackContext) -> int:
        try:
            amount = float(update.message.text.strip().replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            update.message.reply_text("Please enter a valid positive number (e.g. 24.50).")
            return ASK_AMOUNT

        context.user_data[CONTEXT_AMOUNT] = amount

        keyboard = [
            [InlineKeyboardButton(m, callback_data=f'exp_payer:{m}')]
            for m in self._members
        ]
        update.message.reply_text(text="Who paid?", reply_markup=InlineKeyboardMarkup(keyboard))
        return ASK_PAYER

    def add_expense_payer(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data[CONTEXT_PAYER] = query.data.split(":", 1)[1]
        context.user_data[CONTEXT_PARTICIPANTS] = set()
        return self._show_participant_selector(query, context)

    def _show_participant_selector(self, query, context: CallbackContext) -> int:
        selected: set = context.user_data.get(CONTEXT_PARTICIPANTS, set())
        keyboard = []
        for m in self._members:
            label = f"[x] {m}" if m in selected else f"[ ] {m}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f'exp_toggle:{m}')])
        keyboard.append([InlineKeyboardButton("Done", callback_data='exp_participants_done')])
        query.edit_message_text(
            text="Who participated? (tap to toggle, then press Done)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_PARTICIPANTS

    def add_expense_toggle_participant(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        member = query.data.split(":", 1)[1]
        selected: set = context.user_data.setdefault(CONTEXT_PARTICIPANTS, set())
        if member in selected:
            selected.discard(member)
        else:
            selected.add(member)
        return self._show_participant_selector(query, context)

    def add_expense_participants_done(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        selected: set = context.user_data.get(CONTEXT_PARTICIPANTS, set())
        if not selected:
            query.answer(text="Please select at least one participant.", show_alert=True)
            return ASK_PARTICIPANTS
        query.answer()

        description = context.user_data[CONTEXT_DESCRIPTION]
        amount      = context.user_data[CONTEXT_AMOUNT]
        payer       = context.user_data[CONTEXT_PAYER]
        participants_list = sorted(selected)
        share = amount / len(participants_list)

        summary = "\n".join([
            f"Description: {description}",
            f"Amount: \u20ac{amount:.2f}",
            f"Paid by: {payer}",
            f"Participants: {', '.join(participants_list)}",
            f"Each owes: \u20ac{share:.2f}",
            "",
            "Confirm?"
        ])
        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='exp_confirm_yes'),
            InlineKeyboardButton("No",  callback_data='exp_confirm_no'),
        ]]
        query.edit_message_text(text=summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_EXPENSE

    def add_expense_confirm_yes(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        description  = context.user_data[CONTEXT_DESCRIPTION]
        amount       = context.user_data[CONTEXT_AMOUNT]
        payer        = context.user_data[CONTEXT_PAYER]
        participants = sorted(context.user_data[CONTEXT_PARTICIPANTS])

        self._tracker.add_expense(description, amount, payer, participants)

        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(
            text=emojize(f":check_mark_button: Expense '{description}' (\u20ac{amount:.2f}) saved!"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    def add_expense_confirm_no(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(text="Expense cancelled.", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    def cancel_add_expense(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Expense entry cancelled.")
        return ConversationHandler.END

    # ── Settle Up ─────────────────────────────────────────────────────────────

    def settle_start(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data.pop(CONTEXT_SETTLE_PAYER, None)
        context.user_data.pop(CONTEXT_SETTLE_TO, None)
        context.user_data.pop(CONTEXT_SETTLE_AMT, None)

        keyboard = [
            [InlineKeyboardButton(m, callback_data=f'settle_payer:{m}')]
            for m in self._members
        ]
        query.edit_message_text(text="Who is paying?", reply_markup=InlineKeyboardMarkup(keyboard))
        return SETTLE_ASK_PAYER

    def settle_payer(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        payer = query.data.split(":", 1)[1]
        context.user_data[CONTEXT_SETTLE_PAYER] = payer

        receivers = [m for m in self._members if m != payer]
        keyboard = [
            [InlineKeyboardButton(m, callback_data=f'settle_to:{m}')]
            for m in receivers
        ]
        query.edit_message_text(
            text=f"{payer} is paying. Who are they paying?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SETTLE_ASK_RECEIVER

    def settle_receiver(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        receiver = query.data.split(":", 1)[1]
        context.user_data[CONTEXT_SETTLE_TO] = receiver
        payer = context.user_data[CONTEXT_SETTLE_PAYER]
        query.edit_message_text(text=f"How much is {payer} paying {receiver}? (e.g. 15.00)")
        return SETTLE_ASK_AMOUNT

    def settle_amount(self, update: Update, context: CallbackContext) -> int:
        try:
            amount = float(update.message.text.strip().replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            update.message.reply_text("Please enter a valid positive number (e.g. 15.00).")
            return SETTLE_ASK_AMOUNT

        context.user_data[CONTEXT_SETTLE_AMT] = amount
        payer    = context.user_data[CONTEXT_SETTLE_PAYER]
        receiver = context.user_data[CONTEXT_SETTLE_TO]

        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='settle_confirm_yes'),
            InlineKeyboardButton("No",  callback_data='settle_confirm_no'),
        ]]
        update.message.reply_text(
            text=f"{payer} pays {receiver} \u20ac{amount:.2f}\n\nConfirm?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SETTLE_CONFIRM

    def settle_confirm_yes(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        payer    = context.user_data[CONTEXT_SETTLE_PAYER]
        receiver = context.user_data[CONTEXT_SETTLE_TO]
        amount   = context.user_data[CONTEXT_SETTLE_AMT]

        self._tracker.add_settlement(payer, receiver, amount)

        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(
            text=emojize(f":check_mark_button: Settlement recorded: {payer} paid {receiver} \u20ac{amount:.2f}"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    def settle_confirm_no(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(text="Settlement cancelled.", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    def cancel_settle(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Settlement cancelled.")
        return ConversationHandler.END
