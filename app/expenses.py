import sqlite3
from datetime import datetime
from typing import List, Tuple

from .models.expense import Expense
from .models.settlement import Settlement


class ExpenseTracker:

    def __init__(self, config):
        self._db_path = config.EXPENSES_DB_PATH.value or "./expenses.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT    NOT NULL,
                    amount      REAL    NOT NULL,
                    paid_by     TEXT    NOT NULL,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expense_participants (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_id  INTEGER NOT NULL REFERENCES expenses(id),
                    member      TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settlements (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    paid_by     TEXT    NOT NULL,
                    paid_to     TEXT    NOT NULL,
                    amount      REAL    NOT NULL,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.commit()

    def add_expense(self, description: str, amount: float, paid_by: str, participants: List[str]) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO expenses (description, amount, paid_by, created_at) VALUES (?, ?, ?, ?)",
                (description, amount, paid_by, now)
            )
            expense_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO expense_participants (expense_id, member) VALUES (?, ?)",
                [(expense_id, m) for m in participants]
            )
            conn.commit()
        return expense_id

    def list_expenses(self, limit: int = 10) -> List["Expense"]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, description, amount, paid_by, created_at FROM expenses ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result = []
            for row in rows:
                participants = [p["member"] for p in conn.execute(
                    "SELECT member FROM expense_participants WHERE expense_id = ?", (row["id"],)
                ).fetchall()]
                result.append(Expense(
                    id=row["id"], description=row["description"], amount=row["amount"],
                    paid_by=row["paid_by"], participants=participants, created_at=row["created_at"]
                ))
            return result

    def get_expense(self, expense_id: int):
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, description, amount, paid_by, created_at FROM expenses WHERE id = ?",
                (expense_id,)
            ).fetchone()
            if not row:
                return None
            participants = [p["member"] for p in conn.execute(
                "SELECT member FROM expense_participants WHERE expense_id = ?", (expense_id,)
            ).fetchall()]
            return Expense(
                id=row["id"], description=row["description"], amount=row["amount"],
                paid_by=row["paid_by"], participants=participants, created_at=row["created_at"]
            )

    def update_expense(self, expense_id: int, description: str, amount: float, paid_by: str, participants: List[str]) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE expenses SET description=?, amount=?, paid_by=? WHERE id=?",
                (description, amount, paid_by, expense_id)
            )
            conn.execute("DELETE FROM expense_participants WHERE expense_id=?", (expense_id,))
            conn.executemany(
                "INSERT INTO expense_participants (expense_id, member) VALUES (?, ?)",
                [(expense_id, m) for m in participants]
            )
            conn.commit()

    def delete_expense(self, expense_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM expense_participants WHERE expense_id=?", (expense_id,))
            conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
            conn.commit()

    def list_settlements(self, limit: int = 10) -> List["Settlement"]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, paid_by, paid_to, amount, created_at FROM settlements ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [Settlement(
                id=row["id"], paid_by=row["paid_by"], paid_to=row["paid_to"],
                amount=row["amount"], created_at=row["created_at"]
            ) for row in rows]

    def delete_settlement(self, settlement_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM settlements WHERE id=?", (settlement_id,))
            conn.commit()


        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO settlements (paid_by, paid_to, amount, created_at) VALUES (?, ?, ?, ?)",
                (paid_by, paid_to, amount, now)
            )
            conn.commit()
        return cursor.lastrowid

    def get_balances(self) -> List[Tuple[str, str, float]]:
        """Returns list of (debtor, creditor, net_amount) where net_amount > 0.01."""
        gross = {}  # (debtor, creditor) -> float

        with self._get_connection() as conn:
            expenses = conn.execute("SELECT id, amount, paid_by FROM expenses").fetchall()
            for exp in expenses:
                participants = conn.execute(
                    "SELECT member FROM expense_participants WHERE expense_id = ?",
                    (exp["id"],)
                ).fetchall()
                members = [p["member"] for p in participants]
                if not members:
                    continue
                share = exp["amount"] / len(members)
                for member in members:
                    if member == exp["paid_by"]:
                        continue
                    key = (member, exp["paid_by"])
                    gross[key] = gross.get(key, 0.0) + share

            settlements = conn.execute("SELECT paid_by, paid_to, amount FROM settlements").fetchall()
            for s in settlements:
                key = (s["paid_by"], s["paid_to"])
                gross[key] = gross.get(key, 0.0) - s["amount"]

        seen = set()
        results = []
        for debtor, creditor in list(gross.keys()):
            pair = tuple(sorted([debtor, creditor]))
            if pair in seen:
                continue
            seen.add(pair)
            a, b = pair
            net = gross.get((a, b), 0.0) - gross.get((b, a), 0.0)
            if net > 0.01:
                results.append((a, b, round(net, 2)))
            elif net < -0.01:
                results.append((b, a, round(abs(net), 2)))

        return results
