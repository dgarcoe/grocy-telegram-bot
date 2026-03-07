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
(ASK_DESCRIPTION, ASK_AMOUNT, ASK_PAYER, ASK_SPLIT_TYPE, ASK_PARTICIPANTS, ASK_PAID_FOR) = range(6)

# Settle Up conversation states
(SETTLE_ASK_PAYER, SETTLE_ASK_RECEIVER, SETTLE_ASK_AMOUNT) = range(3)

# Manage Expenses conversation states
(MANAGE_EXP_LIST, MANAGE_EXP_ACTION,
 MANAGE_EXP_EDIT_DESC, MANAGE_EXP_EDIT_AMT,
 MANAGE_EXP_EDIT_PAYER, MANAGE_EXP_EDIT_PARTS) = range(6)

# Manage Settlements conversation states
(MANAGE_SET_LIST,) = range(1)

# context.user_data keys
CONTEXT_DESCRIPTION  = "exp_description"
CONTEXT_AMOUNT       = "exp_amount"
CONTEXT_PAYER        = "exp_payer"
CONTEXT_PARTICIPANTS = "exp_participants"
CONTEXT_SPLIT_TYPE   = "exp_split_type"
CONTEXT_PAID_FOR     = "exp_paid_for"
CONTEXT_SETTLE_PAYER = "settle_payer"
CONTEXT_SETTLE_TO    = "settle_to"
CONTEXT_EDIT_ID      = "edit_expense_id"


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
            CallbackQueryHandler(self.noop, pattern='^noop$'),

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
                    ASK_SPLIT_TYPE: [
                        CallbackQueryHandler(self.add_expense_split_equal, pattern='^exp_split:equal$'),
                        CallbackQueryHandler(self.add_expense_split_payfor, pattern='^exp_split:payfor$'),
                    ],
                    ASK_PARTICIPANTS: [
                        CallbackQueryHandler(self.add_expense_toggle_participant, pattern='^exp_toggle:.+$'),
                        CallbackQueryHandler(self.add_expense_participants_done, pattern='^exp_participants_done$'),
                    ],
                    ASK_PAID_FOR: [
                        CallbackQueryHandler(self.add_expense_paid_for, pattern='^exp_payfor:.+$'),
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
                },
                fallbacks=[MessageHandler(Filters.command, self.cancel_settle)],
                allow_reentry=True
            ),

            ConversationHandler(
                entry_points=[CallbackQueryHandler(self.manage_expenses_start, pattern='^manage_expenses$')],
                states={
                    MANAGE_EXP_LIST: [
                        CallbackQueryHandler(self.manage_expense_select, pattern=r'^mexp_select:\d+$'),
                    ],
                    MANAGE_EXP_ACTION: [
                        CallbackQueryHandler(self.manage_expense_delete, pattern=r'^mexp_delete:\d+$'),
                        CallbackQueryHandler(self.manage_expense_edit_start, pattern=r'^mexp_edit:\d+$'),
                        CallbackQueryHandler(self.manage_expenses_start, pattern='^manage_expenses$'),
                    ],
                    MANAGE_EXP_EDIT_DESC: [
                        MessageHandler(Filters.text & ~Filters.command, self.manage_expense_edit_description),
                    ],
                    MANAGE_EXP_EDIT_AMT: [
                        MessageHandler(Filters.text & ~Filters.command, self.manage_expense_edit_amount),
                    ],
                    MANAGE_EXP_EDIT_PAYER: [
                        CallbackQueryHandler(self.manage_expense_edit_payer, pattern='^mexp_payer:.+$'),
                    ],
                    MANAGE_EXP_EDIT_PARTS: [
                        CallbackQueryHandler(self.manage_expense_edit_toggle, pattern='^mexp_toggle:.+$'),
                        CallbackQueryHandler(self.manage_expense_edit_done, pattern='^mexp_parts_done$'),
                    ],
                },
                fallbacks=[MessageHandler(Filters.command, self.cancel_manage_expense)],
                allow_reentry=True
            ),

            ConversationHandler(
                entry_points=[CallbackQueryHandler(self.manage_settlements_start, pattern='^manage_settlements$')],
                states={
                    MANAGE_SET_LIST: [
                        CallbackQueryHandler(self.manage_settlement_delete, pattern=r'^mset_delete:\d+$'),
                    ],
                },
                fallbacks=[],
                allow_reentry=True
            ),
        ]

    # ── Expenses menu ─────────────────────────────────────────────────────────

    def expenses_menu(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        keyboard = [
            [InlineKeyboardButton(emojize(":bar_chart: View Balances"),      callback_data='view_balances')],
            [InlineKeyboardButton(emojize(":plus: Add Expense"),             callback_data='add_expense')],
            [InlineKeyboardButton(emojize(":handshake: Settle Up"),          callback_data='settle_up')],
            [InlineKeyboardButton(emojize(":pencil: Manage Expenses"),       callback_data='manage_expenses')],
            [InlineKeyboardButton(emojize(":wastebasket: Delete Settlement"), callback_data='manage_settlements')],
        ]
        query.edit_message_text(
            text=emojize(":money_bag: Expenses"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    def noop(self, update: Update, context: CallbackContext) -> None:
        update.callback_query.answer()

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
        context.user_data.pop(CONTEXT_SPLIT_TYPE, None)
        context.user_data.pop(CONTEXT_PAID_FOR, None)
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
        keyboard = [
            [InlineKeyboardButton(emojize(":people_with_bunny_ears: Equal split"), callback_data='exp_split:equal')],
            [InlineKeyboardButton(emojize(":person_gesturing_OK: Pay for someone"), callback_data='exp_split:payfor')],
        ]
        query.edit_message_text(
            text="How should this expense be split?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_SPLIT_TYPE

    def add_expense_split_equal(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data[CONTEXT_SPLIT_TYPE] = 'equal'
        return self._show_participant_selector(query, context)

    def add_expense_split_payfor(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data[CONTEXT_SPLIT_TYPE] = 'payfor'
        payer = context.user_data[CONTEXT_PAYER]
        others = [m for m in self._members if m != payer]
        keyboard = [
            [InlineKeyboardButton(m, callback_data=f'exp_payfor:{m}')]
            for m in others
        ]
        query.edit_message_text(
            text=f"{payer} paid for whom?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_PAID_FOR

    def add_expense_paid_for(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        paid_for = query.data.split(":", 1)[1]
        description = context.user_data[CONTEXT_DESCRIPTION]
        amount      = context.user_data[CONTEXT_AMOUNT]
        payer       = context.user_data[CONTEXT_PAYER]

        self._tracker.add_expense(description, amount, payer, [paid_for])

        summary = "\n".join([
            emojize(":check_mark_button: Expense saved!"),
            f"Description: {description}",
            f"Amount: \u20ac{amount:.2f}",
            f"Paid by: {payer}",
            f"Paid for: {paid_for}",
            f"{paid_for} owes: \u20ac{amount:.2f}",
        ])
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(text=summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

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

        description       = context.user_data[CONTEXT_DESCRIPTION]
        amount            = context.user_data[CONTEXT_AMOUNT]
        payer             = context.user_data[CONTEXT_PAYER]
        participants_list = sorted(selected)

        self._tracker.add_expense(description, amount, payer, participants_list)

        share = amount / len(participants_list)
        summary = "\n".join([
            emojize(":check_mark_button: Expense saved!"),
            f"Description: {description}",
            f"Amount: \u20ac{amount:.2f}",
            f"Paid by: {payer}",
            f"Split among: {', '.join(participants_list)}",
            f"Each owes: \u20ac{share:.2f}",
        ])
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(text=summary, reply_markup=InlineKeyboardMarkup(keyboard))
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

        payer    = context.user_data[CONTEXT_SETTLE_PAYER]
        receiver = context.user_data[CONTEXT_SETTLE_TO]

        self._tracker.add_settlement(payer, receiver, amount)

        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        update.message.reply_text(
            text=emojize(f":check_mark_button: Settlement recorded: {payer} paid {receiver} \u20ac{amount:.2f}"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    def cancel_settle(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Settlement cancelled.")
        return ConversationHandler.END

    # ── Manage Expenses ───────────────────────────────────────────────────────

    def manage_expenses_start(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        expenses = self._tracker.list_expenses()
        if not expenses:
            keyboard = [[InlineKeyboardButton("Back", callback_data='expenses')]]
            query.edit_message_text(text="No expenses recorded yet.", reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
        keyboard = [
            [InlineKeyboardButton(f"{e.description} \u20ac{e.amount:.2f}", callback_data=f'mexp_select:{e.id}')]
            for e in expenses
        ]
        keyboard.append([InlineKeyboardButton("Back", callback_data='expenses')])
        query.edit_message_text(
            text="Select an expense to edit or delete:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MANAGE_EXP_LIST

    def manage_expense_select(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        expense_id = int(query.data.split(":", 1)[1])
        exp = self._tracker.get_expense(expense_id)
        if not exp:
            query.edit_message_text("Expense not found.")
            return ConversationHandler.END
        is_pay_for = len(exp.participants) == 1 and exp.participants[0] != exp.paid_by
        if is_pay_for:
            text = "\n".join([
                f"Description: {exp.description}",
                f"Amount: \u20ac{exp.amount:.2f}",
                f"Paid by: {exp.paid_by}",
                f"Paid for: {exp.participants[0]}",
                f"{exp.participants[0]} owes: \u20ac{exp.amount:.2f}",
            ])
        else:
            share = exp.amount / len(exp.participants) if exp.participants else 0
            text = "\n".join([
                f"Description: {exp.description}",
                f"Amount: \u20ac{exp.amount:.2f}",
                f"Paid by: {exp.paid_by}",
                f"Split among: {', '.join(exp.participants)}",
                f"Each owes: \u20ac{share:.2f}",
            ])
        keyboard = [
            [
                InlineKeyboardButton("Edit",   callback_data=f'mexp_edit:{expense_id}'),
                InlineKeyboardButton("Delete", callback_data=f'mexp_delete:{expense_id}'),
            ],
            [InlineKeyboardButton("Back", callback_data='manage_expenses')],
        ]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MANAGE_EXP_ACTION

    def manage_expense_delete(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        expense_id = int(query.data.split(":", 1)[1])
        exp = self._tracker.get_expense(expense_id)
        self._tracker.delete_expense(expense_id)
        desc = exp.description if exp else f"#{expense_id}"
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(
            text=emojize(f":wastebasket: Expense '{desc}' deleted."),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    def manage_expense_edit_start(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        expense_id = int(query.data.split(":", 1)[1])
        context.user_data[CONTEXT_EDIT_ID] = expense_id
        exp = self._tracker.get_expense(expense_id)
        context.user_data[CONTEXT_PARTICIPANTS] = set(exp.participants) if exp else set()
        query.edit_message_text(
            text=f"Editing: {exp.description}\n\nNew description:"
        )
        return MANAGE_EXP_EDIT_DESC

    def manage_expense_edit_description(self, update: Update, context: CallbackContext) -> int:
        context.user_data[CONTEXT_DESCRIPTION] = update.message.text.strip()
        update.message.reply_text("New amount? (e.g. 24.50)")
        return MANAGE_EXP_EDIT_AMT

    def manage_expense_edit_amount(self, update: Update, context: CallbackContext) -> int:
        try:
            amount = float(update.message.text.strip().replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            update.message.reply_text("Please enter a valid positive number.")
            return MANAGE_EXP_EDIT_AMT
        context.user_data[CONTEXT_AMOUNT] = amount
        keyboard = [
            [InlineKeyboardButton(m, callback_data=f'mexp_payer:{m}')]
            for m in self._members
        ]
        update.message.reply_text("Who paid?", reply_markup=InlineKeyboardMarkup(keyboard))
        return MANAGE_EXP_EDIT_PAYER

    def manage_expense_edit_payer(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        context.user_data[CONTEXT_PAYER] = query.data.split(":", 1)[1]
        return self._show_edit_participant_selector(query, context)

    def _show_edit_participant_selector(self, query, context: CallbackContext) -> int:
        selected: set = context.user_data.get(CONTEXT_PARTICIPANTS, set())
        keyboard = []
        for m in self._members:
            label = f"[x] {m}" if m in selected else f"[ ] {m}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f'mexp_toggle:{m}')])
        keyboard.append([InlineKeyboardButton("Done", callback_data='mexp_parts_done')])
        query.edit_message_text(
            text="Who participated? (tap to toggle, then press Done)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MANAGE_EXP_EDIT_PARTS

    def manage_expense_edit_toggle(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        member = query.data.split(":", 1)[1]
        selected: set = context.user_data.setdefault(CONTEXT_PARTICIPANTS, set())
        if member in selected:
            selected.discard(member)
        else:
            selected.add(member)
        return self._show_edit_participant_selector(query, context)

    def manage_expense_edit_done(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        selected: set = context.user_data.get(CONTEXT_PARTICIPANTS, set())
        if not selected:
            query.answer(text="Please select at least one participant.", show_alert=True)
            return MANAGE_EXP_EDIT_PARTS
        query.answer()
        expense_id   = context.user_data[CONTEXT_EDIT_ID]
        description  = context.user_data[CONTEXT_DESCRIPTION]
        amount       = context.user_data[CONTEXT_AMOUNT]
        payer        = context.user_data[CONTEXT_PAYER]
        participants = sorted(selected)
        self._tracker.update_expense(expense_id, description, amount, payer, participants)
        is_pay_for = len(participants) == 1 and participants[0] != payer
        if is_pay_for:
            summary = "\n".join([
                emojize(":check_mark_button: Expense updated!"),
                f"Description: {description}",
                f"Amount: \u20ac{amount:.2f}",
                f"Paid by: {payer}",
                f"Paid for: {participants[0]}",
                f"{participants[0]} owes: \u20ac{amount:.2f}",
            ])
        else:
            share = amount / len(participants)
            summary = "\n".join([
                emojize(":check_mark_button: Expense updated!"),
                f"Description: {description}",
                f"Amount: \u20ac{amount:.2f}",
                f"Paid by: {payer}",
                f"Split among: {', '.join(participants)}",
                f"Each owes: \u20ac{share:.2f}",
            ])
        keyboard = [[InlineKeyboardButton("Back to Expenses", callback_data='expenses')]]
        query.edit_message_text(text=summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    def cancel_manage_expense(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Cancelled.")
        return ConversationHandler.END

    # ── Manage Settlements ────────────────────────────────────────────────────

    def manage_settlements_start(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        return self._show_settlements_list(query)

    def _show_settlements_list(self, query, deleted_msg: str = None) -> int:
        settlements = self._tracker.list_settlements()
        if not settlements:
            text = emojize(":wastebasket: Deleted. No more settlements.") if deleted_msg else "No settlements recorded yet."
            keyboard = [[InlineKeyboardButton("Back", callback_data='expenses')]]
            query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{s.paid_by} \u2192 {s.paid_to} \u20ac{s.amount:.2f}",
                    callback_data='noop'
                ),
                InlineKeyboardButton(emojize(":wastebasket:"), callback_data=f'mset_delete:{s.id}'),
            ]
            for s in settlements
        ]
        keyboard.append([InlineKeyboardButton("Back", callback_data='expenses')])
        text = emojize(":wastebasket: Deleted. Remaining:") if deleted_msg else "Tap the trash icon to delete a settlement:"
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MANAGE_SET_LIST

    def manage_settlement_delete(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        settlement_id = int(query.data.split(":", 1)[1])
        self._tracker.delete_settlement(settlement_id)
        return self._show_settlements_list(query, deleted_msg=True)
