import sqlite3
from pathlib import Path
from typing import Iterable

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETE = "complete"


class DB:
    def __init__(self, db_file: str):
        self.db_file = str(Path(db_file))
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    model_id INTEGER NOT NULL,
                    order_status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )
            conn.commit()

    def pull(self, decoded: bool = True, order_status: str | None = None):
        query = "SELECT order_id, model_id, order_status FROM orders"
        params: list[object] = []
        if order_status is not None:
            query += " WHERE order_status = ?"
            params.append(order_status)
        query += " ORDER BY order_id ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return rows

    def update_status(self, order_id: int, new_status: str):
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE orders SET order_status = ? WHERE order_id = ?",
                (new_status, order_id),
            )
            conn.commit()
        return cur.rowcount

    def insert_order(self, order_id: int, model_id: int, status: str = STATUS_PENDING):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO orders (order_id, model_id, order_status) VALUES (?, ?, ?)",
                (order_id, model_id, status),
            )
            conn.commit()


def rows_to_dicts(rows: Iterable[sqlite3.Row]):
    return [dict(row) for row in rows]
