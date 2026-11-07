"""Persistence of the paper-trading account as the plain dict the simulation works on.

Trades and equity rows are append-only, so a save inserts only the rows that are new."""

from __future__ import annotations

import json
from contextlib import closing

from app.db import connect

TRADE_COLUMNS = ("date", "symbol", "side", "shares", "price", "value", "fee")
EQUITY_COLUMNS = ("date", "cash", "value", "equity")


def load_account(account_id: int | None = None) -> dict | None:
    """The account with `account_id`, or the oldest one when omitted (there is a single account for now)."""
    with closing(connect()) as db:
        row = (db.execute("SELECT * FROM account WHERE id = ?", (account_id,)) if account_id
               else db.execute("SELECT * FROM account ORDER BY id LIMIT 1")).fetchone()
        if row is None:
            return None
        key = (row["id"],)
        return {
            "id": row["id"], "replay": bool(row["replay"]), "weights": json.loads(row["weights"]), "slippage_bps": row["slippage_bps"],
            "params": {name: row[name] for name in ("top_fraction", "buffer", "min_hold", "min_score", "sizing", "sell_score")},
            "initial_capital": row["initial_capital"], "start_date": row["start_date"], "last_date": row["last_date"],
            "cash": row["cash"],
            "positions": {r["symbol"]: {"shares": r["shares"], "held": r["held"], "cost": r["cost"]}
                          for r in db.execute("SELECT symbol, shares, held, cost FROM position WHERE account_id = ?", key)},
            "trades": [dict(r) for r in db.execute(
                f"SELECT {', '.join(TRADE_COLUMNS)} FROM trade WHERE account_id = ? ORDER BY id", key)],
            "equity": [dict(r) for r in db.execute(
                f"SELECT {', '.join(EQUITY_COLUMNS)} FROM equity WHERE account_id = ? ORDER BY date", key)],
        }


def save_account(account: dict) -> None:
    """Insert the account on first save (sets account["id"]); afterwards only cash, last_date, positions and new rows change."""
    with closing(connect()) as db, db:
        if "id" not in account:
            params = account["params"]
            account["id"] = db.execute(
                "INSERT INTO account (weights, top_fraction, buffer, min_hold, min_score, sizing, sell_score, slippage_bps,"
                " initial_capital, start_date, last_date, cash, replay) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (json.dumps(account["weights"]), params["top_fraction"], params["buffer"], params["min_hold"],
                 params["min_score"], params["sizing"], params["sell_score"], account["slippage_bps"], account["initial_capital"], account["start_date"],
                 account["last_date"], account["cash"], int(account.get("replay", False))),
            ).lastrowid
        else:
            db.execute("UPDATE account SET last_date = ?, cash = ? WHERE id = ?",
                       (account["last_date"], account["cash"], account["id"]))
        key = account["id"]
        db.execute("DELETE FROM position WHERE account_id = ?", (key,))
        db.executemany("INSERT INTO position VALUES (?, ?, ?, ?, ?)",
                       [(key, symbol, p["shares"], p["held"], p["cost"]) for symbol, p in account["positions"].items()])
        for table, columns, rows in (("trade", TRADE_COLUMNS, account["trades"]), ("equity", EQUITY_COLUMNS, account["equity"])):
            saved = db.execute(f"SELECT COUNT(*) FROM {table} WHERE account_id = ?", (key,)).fetchone()[0]
            db.executemany(f"INSERT INTO {table} (account_id, {', '.join(columns)}) VALUES (?{', ?' * len(columns)})",
                           [(key, *(row[column] for column in columns)) for row in rows[saved:]])


def delete_account(account_id: int) -> None:
    with closing(connect()) as db, db:
        db.execute("DELETE FROM account WHERE id = ?", (account_id,))
