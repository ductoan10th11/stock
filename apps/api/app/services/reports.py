"""Daily profit and loss report of the paper-trading account, sent once per processed session."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime

from app.db import connect
from app.schemas.paper import PaperState
from app.services import subscribers, telegram
from app.services.catalog import MODEL, STRATEGY_BY_ID
from app.services.market import MODEL_NAME
from app.services.paper_service import read_state
from crawl import VN

logger = logging.getLogger("uvicorn.error")


def percent(value: float) -> str:
    return f"{value:+.2%}".replace(".", ",")


def money(value: float) -> str:
    """Whole dong with thousands separators, so the figure matches the account to the last dong."""
    return f"{round(value):,}"


def day_change(state: PaperState) -> float:
    curve = state.equity.account
    return curve[-1] / (curve[-2] if len(curve) > 1 else 1.0) - 1


def strategy_line(weights: dict[str, float]) -> str:
    names = [name for name, weight in weights.items() if weight]
    if names == [MODEL]:
        return f"Mô hình: {MODEL_NAME}"
    return "Chiến thuật: " + " + ".join(STRATEGY_BY_ID[name].label for name in names)


def daily_message(state: PaperState) -> str:
    account, summary = state.account, state.summary
    date = datetime.strptime(account.last_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    lines = [
        f"Paper trading {date}",
        strategy_line(account.weights),
        "",
        f"Vốn: {money(account.initial_capital)}",
        f"Tài khoản: {money(summary.equity)}",
        f"Hôm nay: {percent(day_change(state))}",
        f"Lãi/lỗ: {round(summary.gain):+,} ({percent(summary.gain_pct)})",
        f"Tiền mặt: {summary.cash_pct:.0%}",
        "",
        f"Đang giữ ({len(state.positions)}):",
    ]
    lines += [f"{p.symbol} {percent(p.pnl_pct)}" for p in sorted(state.positions, key=lambda p: -p.value)] or ["chưa có vị thế"]
    buys = [o.symbol for o in state.orders if o.action == "buy"]
    sells = [o.symbol for o in state.orders if o.action == "sell"]
    plan = [f"{label} {', '.join(symbols)}" for label, symbols in (("mua", buys), ("bán", sells)) if symbols]
    lines += ["", "Lệnh phiên tới: " + ("; ".join(plan) or "không đổi")]
    return "\n".join(lines)


def broadcast(message: str) -> None:
    """The owner's send decides success (a failure there is retried); a failing subscriber must not block the others."""
    telegram.send(message)
    for chat_id in subscribers.approved():
        if chat_id == telegram.admin_id():
            continue
        try:
            telegram.send_to(chat_id, message)
        except Exception:
            logger.exception("report to subscriber %s failed", chat_id)


def send_daily_report() -> bool:
    """Idempotent per session date, so a retry after a failure never sends a duplicate."""
    if not telegram.configured():
        return False
    state = read_state()
    if not (state.account and state.summary):
        return False
    account_id, date = state.account.id, state.account.last_date
    with closing(connect()) as database:
        if database.execute("SELECT 1 FROM daily_report WHERE account_id = ? AND date = ?", (account_id, date)).fetchone():
            return False
    message = daily_message(state)
    broadcast(message)
    with closing(connect()) as database, database:
        database.execute(
            "INSERT INTO daily_report VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_id, date, datetime.now(VN).isoformat(timespec="seconds"), state.summary.equity, state.summary.gain_pct,
             day_change(state), message),
        )
    return True
