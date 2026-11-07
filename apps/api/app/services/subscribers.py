"""People who asked the bot for the daily report; only approved ones receive it."""

from __future__ import annotations

from contextlib import closing

from app.db import connect


def get(chat_id: int) -> dict | None:
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM telegram_user WHERE chat_id = ?", (chat_id,)).fetchone()
    return dict(row) if row else None


def set_status(chat_id: int, status: str, user: dict | None = None) -> None:
    """Creates the row on first sight of a user, afterwards only the status changes."""
    with closing(connect()) as db, db:
        db.execute(
            "INSERT INTO telegram_user (chat_id, username, first_name, status, decided_at)"
            " VALUES (?, ?, ?, ?, CASE WHEN ? = 'pending' THEN NULL ELSE CURRENT_TIMESTAMP END)"
            " ON CONFLICT (chat_id) DO UPDATE SET status = excluded.status, decided_at = excluded.decided_at",
            (chat_id, (user or {}).get("username"), (user or {}).get("first_name"), status, status),
        )


def approved() -> list[int]:
    with closing(connect()) as db:
        return [row[0] for row in db.execute("SELECT chat_id FROM telegram_user WHERE status = 'approved' ORDER BY chat_id")]
