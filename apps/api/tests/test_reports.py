import pytest

from app.schemas.common import PortfolioParams
from app.schemas.paper import AccountInfo, EquityCurve, Order, PaperState, Position, Summary
from app.db import connect
from app.services import reports, telegram
from app.services.account_store import save_account
from app.services.paper import new_account
from app.services.engine import Params


def make_state(last_date: str = "2026-11-09") -> PaperState:
    return PaperState(
        data_ready=True, trained_until="2026-11-04", latest_candle=last_date, score_ready=True, signal_date=last_date,
        account=AccountInfo(id=1, replay=False, weights={"model": 1.0}, params=PortfolioParams(), initial_capital=1e9, slippage_bps=10,
                            start_date="2026-11-06", last_date=last_date),
        summary=Summary(equity=1.02e9, cash=1.2e8, gain=2e7, gain_pct=0.02, cash_pct=0.12, equal_weight_return=0.012,
                        vnindex_return=None),
        equity=EquityCurve(dates=["2026-11-06", last_date], account=[1.0, 1.02], equal_weight=[1.0, 1.012], vnindex=None),
        positions=[Position(symbol="PVD", shares=100, cost=17000, price=17340, pnl_pct=0.02, value=1.7e6, held=1)],
        orders=[Order(symbol="DPM", action="buy", shares=100, price=19650, value=1.9e6),
                Order(symbol="PVD", action="sell", shares=100, price=17340, value=1.7e6)],
    )


@pytest.fixture
def sent(monkeypatch):
    messages = []
    save_account(new_account({"model": 1.0}, Params(), 1e9, "2026-11-06"))
    monkeypatch.setattr(telegram, "configured", lambda: True)
    monkeypatch.setattr(telegram, "send", messages.append)
    monkeypatch.setattr(reports, "read_state", make_state)
    return messages


def test_message_reports_profit_positions_and_plan():
    text = reports.daily_message(make_state())
    assert "Paper trading 09/11/2026" in text
    assert "Tài khoản: 1,02 tỷ (+2,00%)" in text
    assert "Hôm nay: +2,00%" in text
    assert "Lãi/lỗ: +20,0 triệu" in text
    assert "PVD +2,00%" in text
    assert "Lệnh phiên tới: mua DPM; bán PVD" in text


def test_report_is_sent_once_per_session_and_stored(sent):
    assert reports.send_daily_report() is True
    assert reports.send_daily_report() is False
    assert len(sent) == 1
    rows = connect().execute("SELECT account_id, date, equity, gain_pct FROM daily_report").fetchall()
    assert [tuple(row) for row in rows] == [(1, "2026-11-09", 1.02e9, 0.02)]


def test_failed_send_is_not_recorded_so_it_can_retry(sent, monkeypatch):
    def fail(_):
        raise OSError("telegram down")

    monkeypatch.setattr(telegram, "send", fail)
    with pytest.raises(OSError):
        reports.send_daily_report()
    assert connect().execute("SELECT COUNT(*) FROM daily_report").fetchone()[0] == 0


def test_nothing_is_sent_without_telegram_config_or_sessions(sent, monkeypatch):
    monkeypatch.setattr(telegram, "configured", lambda: False)
    assert reports.send_daily_report() is False
    monkeypatch.setattr(telegram, "configured", lambda: True)
    monkeypatch.setattr(reports, "read_state", lambda: make_state().model_copy(update={"summary": None}))
    assert reports.send_daily_report() is False
    assert sent == []
