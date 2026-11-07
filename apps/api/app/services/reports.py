"""Daily profit and loss report of the paper-trading account, sent once per processed session."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime

from app.db import connect
from app.schemas.paper import PaperState
from app.services import telegram
from app.services.catalog import STRATEGY_BY_ID
from app.services.paper_service import read_state
from crawl import VN

def percent(value: float) -> str:
    return f"{value:+.2%}".replace(".", ",")


def vnd(value: float) -> str:
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f} tỷ".replace(".", ",")
    return f"{value / 1e6:.1f} triệu".replace(".", ",")


def day_change(state: PaperState) -> float:
    curve = state.equity.account
    return curve[-1] / (curve[-2] if len(curve) > 1 else 1.0) - 1


def daily_message(state: PaperState) -> str:
    account, summary = state.account, state.summary
    date = datetime.strptime(account.last_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    strategy = " + ".join(STRATEGY_BY_ID[name].label for name, weight in account.weights.items() if weight)
    gain_icon = "🟢" if summary.gain >= 0 else "🔴"
    lines = [
        f"{gain_icon} Paper trading {date}",
        f"Chiến thuật: {strategy}",
        "",
        f"Tài khoản: {vnd(summary.equity)} ({percent(summary.gain_pct)})",
        f"Hôm nay: {percent(day_change(state))}",
        f"Lãi/lỗ: {'+' if summary.gain >= 0 else '-'}{vnd(abs(summary.gain))}",
        f"Tiền mặt: {summary.cash_pct:.0%}",
    ]
    benchmarks = [("cân bằng đều", summary.equal_weight_return), ("VN-Index", summary.vnindex_return)]
    lines.append("Cùng kỳ: " + ", ".join(f"{name} {percent(value)}" for name, value in benchmarks if value is not None))
    lines += ["", f"Đang giữ ({len(state.positions)}):"]
    lines += [f"{p.symbol} {percent(p.pnl_pct)}" for p in sorted(state.positions, key=lambda p: -p.value)] or ["chưa có vị thế"]
    buys = [o.symbol for o in state.orders if o.action == "buy"]
    sells = [o.symbol for o in state.orders if o.action == "sell"]
    plan = [f"{label} {', '.join(symbols)}" for label, symbols in (("mua", buys), ("bán", sells)) if symbols]
    lines += ["", "Lệnh phiên tới: " + ("; ".join(plan) or "không đổi")]
    return "\n".join(lines)


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
    telegram.send(message)
    with closing(connect()) as database, database:
        database.execute(
            "INSERT INTO daily_report VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_id, date, datetime.now(VN).isoformat(timespec="seconds"), state.summary.equity, state.summary.gain_pct,
             day_change(state), message),
        )
    return True
