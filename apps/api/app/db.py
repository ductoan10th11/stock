"""SQLite for paper trading. Schema changes go at the end of MIGRATIONS; `PRAGMA user_version` records how many ran."""

from __future__ import annotations

import sqlite3

from app.core.config import PAPER_DB_PATH

# Prices and costs are in thousand VND, the unit the engine and the price data use. Dates are ISO text (YYYY-MM-DD).
# Every child table keys on account_id, so more accounts (for example one per web user) need no schema change.
MIGRATIONS = [
    """
    CREATE TABLE account (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL DEFAULT 'default',
        weights TEXT NOT NULL,
        top_fraction REAL NOT NULL,
        buffer REAL NOT NULL,
        min_hold INTEGER NOT NULL,
        min_score REAL,
        slippage_bps REAL NOT NULL,
        initial_capital REAL NOT NULL,
        start_date TEXT NOT NULL,
        last_date TEXT NOT NULL,
        cash REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE position (
        account_id INTEGER NOT NULL REFERENCES account (id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        shares INTEGER NOT NULL CHECK (shares > 0),
        held INTEGER NOT NULL,
        cost REAL NOT NULL,
        PRIMARY KEY (account_id, symbol)
    ) WITHOUT ROWID;

    CREATE TABLE trade (
        id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES account (id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
        shares INTEGER NOT NULL CHECK (shares > 0),
        price REAL NOT NULL,
        value REAL NOT NULL,
        fee REAL NOT NULL
    );
    CREATE INDEX trade_account_date ON trade (account_id, date);

    CREATE TABLE equity (
        account_id INTEGER NOT NULL REFERENCES account (id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        cash REAL NOT NULL,
        value REAL NOT NULL,
        equity REAL NOT NULL,
        PRIMARY KEY (account_id, date)
    ) WITHOUT ROWID;

    CREATE TABLE daily_report (
        account_id INTEGER NOT NULL REFERENCES account (id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        equity REAL NOT NULL,
        gain_pct REAL NOT NULL,
        day_pct REAL NOT NULL,
        message TEXT NOT NULL,
        PRIMARY KEY (account_id, date)
    ) WITHOUT ROWID;
    """,
    "ALTER TABLE account ADD COLUMN sizing TEXT NOT NULL DEFAULT 'equal';",
    "ALTER TABLE account ADD COLUMN sell_score REAL;",
    "ALTER TABLE account ADD COLUMN replay INTEGER NOT NULL DEFAULT 0;",
    """
    CREATE TABLE telegram_user (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
        requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        decided_at TEXT
    ) WITHOUT ROWID;
    """,
]


def connect() -> sqlite3.Connection:
    PAPER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(PAPER_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        connection.executescript(f"BEGIN;{script}PRAGMA user_version = {number};COMMIT;")
    return connection
