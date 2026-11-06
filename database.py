"""Работа с SQLite: склад ключей и заказы."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Iterable

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS keys (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    value    TEXT NOT NULL UNIQUE,
    status   TEXT NOT NULL DEFAULT 'available',  -- available | reserved | sold
    order_id INTEGER,
    added_at TEXT NOT NULL,
    sold_at  TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    username   TEXT,
    full_name  TEXT,
    method     TEXT NOT NULL,                    -- stars | sber
    status     TEXT NOT NULL DEFAULT 'pending',  -- pending | review | paid | declined | expired
    price      INTEGER NOT NULL,
    key_id     INTEGER,
    key_value  TEXT,
    charge_id  TEXT UNIQUE,
    proof_chat_id    INTEGER,
    proof_message_id INTEGER,
    created_at TEXT NOT NULL,
    paid_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_keys_status ON keys(status);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
"""

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("База данных не инициализирована. Вызовите database.init().")
    return _conn


def init() -> None:
    global _conn
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA foreign_keys=ON")
    _conn.executescript(SCHEMA)
    _conn.commit()


# --------------------------------------------------------------------------- #
#  Склад ключей
# --------------------------------------------------------------------------- #
def add_keys(values: Iterable[str]) -> tuple[int, int]:
    """Добавляет ключи. Возвращает (добавлено, пропущено)."""
    added = skipped = 0
    with _lock, _db():
        for value in values:
            try:
                _db().execute(
                    "INSERT INTO keys(value, status, added_at) VALUES(?, 'available', ?)",
                    (value, _now()),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return added, skipped


def stock_count() -> int:
    with _lock:
        row = _db().execute(
            "SELECT COUNT(*) FROM keys WHERE status='available'"
        ).fetchone()
        return int(row[0])


def total_keys() -> int:
    with _lock:
        row = _db().execute("SELECT COUNT(*) FROM keys").fetchone()
        return int(row[0])


# --------------------------------------------------------------------------- #
#  Заказы
# --------------------------------------------------------------------------- #
def _order_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def get_order(order_id: int) -> dict | None:
    with _lock:
        row = _db().execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return _order_dict(row)


def get_active_sber_order(user_id: int) -> dict | None:
    with _lock:
        row = _db().execute(
            "SELECT * FROM orders "
            "WHERE user_id=? AND method='sber' AND status IN ('pending','review') "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return _order_dict(row)


def create_pending_order(
    user_id: int,
    username: str | None,
    full_name: str | None,
    method: str,
    price: int,
) -> int:
    """Создаёт заказ без резерва ключа (для звёзд)."""
    with _lock, _db():
        cur = _db().execute(
            "INSERT INTO orders(user_id, username, full_name, method, status, price, created_at) "
            "VALUES(?,?,?,?,'pending',?,?)",
            (user_id, username, full_name, method, price, _now()),
        )
        return int(cur.lastrowid)


def create_sber_order(
    user_id: int,
    username: str | None,
    full_name: str | None,
    price: int,
) -> dict | None:
    """Создаёт заказ на Сбер и сразу резервирует под него ключ."""
    with _lock, _db():
        key = _db().execute(
            "SELECT id, value FROM keys WHERE status='available' ORDER BY id LIMIT 1"
        ).fetchone()
        if key is None:
            return None

        cur = _db().execute(
            "INSERT INTO orders(user_id, username, full_name, method, status, price, created_at) "
            "VALUES(?,?,?,'sber','pending',?,?)",
            (user_id, username, full_name, price, _now()),
        )
        order_id = int(cur.lastrowid)
        _db().execute(
            "UPDATE keys SET status='reserved', order_id=? "
            "WHERE id=? AND status='available'",
            (order_id, key["id"]),
        )
        return get_order(order_id)


def save_proof(order_id: int, chat_id: int, message_id: int) -> None:
    with _lock, _db():
        _db().execute(
            "UPDATE orders SET proof_chat_id=?, proof_message_id=? WHERE id=?",
            (chat_id, message_id, order_id),
        )


def set_order_status(order_id: int, status: str) -> bool:
    """Меняет статус заказа, только если он ещё не финальный."""
    with _lock, _db():
        cur = _db().execute(
            "UPDATE orders SET status=? WHERE id=? AND status IN ('pending','review')",
            (status, order_id),
        )
        return cur.rowcount > 0


def confirm_order(order_id: int, charge_id: str | None = None) -> tuple[str | None, str | None]:
    """Подтверждает оплату и выдаёт ключ.

    Возвращает (ключ, ошибка). Ошибки: "already", "no_keys".
    """
    with _lock:
        conn = _db()

        if charge_id:
            used = conn.execute(
                "SELECT 1 FROM orders WHERE charge_id=?", (charge_id,)
            ).fetchone()
            if used:
                return None, "already"

        try:
            with conn:
                order = conn.execute(
                    "SELECT * FROM orders WHERE id=?", (order_id,)
                ).fetchone()
                if order is None or order["status"] not in ("pending", "review"):
                    return None, "already"

                key = conn.execute(
                    "SELECT id, value FROM keys WHERE order_id=? AND status='reserved'",
                    (order_id,),
                ).fetchone()
                if key is None:
                    key = conn.execute(
                        "SELECT id, value FROM keys WHERE status='available' ORDER BY id LIMIT 1"
                    ).fetchone()
                    if key is None:
                        return None, "no_keys"
                    conn.execute(
                        "UPDATE keys SET status='reserved', order_id=? "
                        "WHERE id=? AND status='available'",
                        (order_id, key["id"]),
                    )

                conn.execute(
                    "UPDATE keys SET status='sold', sold_at=? WHERE id=?",
                    (_now(), key["id"]),
                )
                conn.execute(
                    "UPDATE orders SET status='paid', key_id=?, key_value=?, paid_at=?, "
                    "charge_id=COALESCE(?, charge_id) WHERE id=?",
                    (key["id"], key["value"], _now(), charge_id, order_id),
                )
            return key["value"], None
        except sqlite3.IntegrityError:
            conn.rollback()
            return None, "already"


def decline_order(order_id: int) -> dict | None:
    """Отклоняет заказ и возвращает зарезервированный ключ на склад."""
    with _lock, _db():
        order = _db().execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if order is None or order["status"] not in ("pending", "review"):
            return None
        _db().execute(
            "UPDATE keys SET status='available', order_id=NULL "
            "WHERE order_id=? AND status='reserved'",
            (order_id,),
        )
        _db().execute("UPDATE orders SET status='declined' WHERE id=?", (order_id,))
        return _order_dict(order)


def expire_old_orders(ttl_hours: int) -> list[dict]:
    """Отменяет неоплаченные заказы старше ttl_hours и освобождает ключи."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    ).isoformat(timespec="seconds")
    expired: list[dict] = []

    with _lock, _db():
        rows = _db().execute(
            "SELECT * FROM orders WHERE status='pending' AND created_at < ?",
            (cutoff,),
        ).fetchall()
        for row in rows:
            _db().execute(
                "UPDATE keys SET status='available', order_id=NULL "
                "WHERE order_id=? AND status='reserved'",
                (row["id"],),
            )
            _db().execute("UPDATE orders SET status='expired' WHERE id=?", (row["id"],))
            expired.append(dict(row))
    return expired


def review_orders() -> list[dict]:
    with _lock:
        rows = _db().execute(
            "SELECT * FROM orders WHERE status='review' ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def user_keys(user_id: int, limit: int = 5) -> list[dict]:
    with _lock:
        rows = _db().execute(
            "SELECT * FROM orders WHERE user_id=? AND status='paid' "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def stats() -> dict:
    with _lock:
        def count(sql: str, params: tuple = ()) -> int:
            return int(_db().execute(sql, params).fetchone()[0])

        available = count("SELECT COUNT(*) FROM keys WHERE status='available'")
        reserved = count("SELECT COUNT(*) FROM keys WHERE status='reserved'")
        sold = count("SELECT COUNT(*) FROM keys WHERE status='sold'")
        review = count("SELECT COUNT(*) FROM orders WHERE status='review'")
        rub_revenue = count(
            "SELECT COALESCE(SUM(price),0) FROM orders "
            "WHERE status='paid' AND method='sber'"
        )
        stars_sales = count(
            "SELECT COUNT(*) FROM orders WHERE status='paid' AND method='stars'"
        )
        return {
            "available": available,
            "reserved": reserved,
            "sold": sold,
            "review": review,
            "rub_revenue": rub_revenue,
            "stars_sales": stars_sales,
        }
