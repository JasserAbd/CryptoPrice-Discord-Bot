"""SQLite storage for per-server config and price alerts.

Two tables:
  - guild_config: one row per Discord server (default coin, custom logo, exchange, quote)
  - alerts:       price alerts users have set
"""
import sqlite3
import threading
from typing import Optional

import config

# One connection guarded by a lock. discord.py runs on a single event loop,
# and SQLite writes here are tiny, so a simple lock is plenty.
_conn: Optional[sqlite3.Connection] = None
_lock = threading.Lock()


def init() -> None:
    global _conn
    _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    with _lock:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id   INTEGER PRIMARY KEY,
                coin       TEXT    DEFAULT 'BTC',
                logo_url   TEXT,
                exchange   TEXT,
                quote      TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                guild_id   INTEGER,
                coin       TEXT    NOT NULL,
                direction  TEXT    NOT NULL,   -- 'above' or 'below'
                target     REAL    NOT NULL,
                exchange   TEXT,
                quote      TEXT,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _conn.commit()


# --------------------------------------------------------------------------- #
# Guild config
# --------------------------------------------------------------------------- #
def get_guild_config(guild_id: int) -> dict:
    """Return the config row for a guild, creating defaults if missing."""
    with _lock:
        row = _conn.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        if row is None:
            _conn.execute(
                "INSERT INTO guild_config (guild_id, coin, exchange, quote) VALUES (?, ?, ?, ?)",
                (guild_id, "BTC", config.DEFAULT_EXCHANGE, config.DEFAULT_QUOTE),
            )
            _conn.commit()
            row = _conn.execute(
                "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
            ).fetchone()
    return dict(row)


def set_guild_field(guild_id: int, field: str, value) -> None:
    if field not in {"coin", "logo_url", "exchange", "quote"}:
        raise ValueError(f"Unknown config field: {field}")
    get_guild_config(guild_id)  # ensure the row exists
    with _lock:
        _conn.execute(
            f"UPDATE guild_config SET {field} = ? WHERE guild_id = ?", (value, guild_id)
        )
        _conn.commit()


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
def add_alert(
    user_id: int,
    channel_id: int,
    guild_id: Optional[int],
    coin: str,
    direction: str,
    target: float,
    exchange: str,
    quote: str,
) -> int:
    with _lock:
        cur = _conn.execute(
            """INSERT INTO alerts
               (user_id, channel_id, guild_id, coin, direction, target, exchange, quote)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, channel_id, guild_id, coin, direction, target, exchange, quote),
        )
        _conn.commit()
        return cur.lastrowid


def get_all_alerts() -> list[dict]:
    with _lock:
        rows = _conn.execute("SELECT * FROM alerts").fetchall()
    return [dict(r) for r in rows]


def get_user_alerts(user_id: int) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_alert(alert_id: int, user_id: Optional[int] = None) -> bool:
    with _lock:
        if user_id is None:
            cur = _conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        else:
            cur = _conn.execute(
                "DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
            )
        _conn.commit()
        return cur.rowcount > 0
