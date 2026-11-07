import shutil
import time

from app.core.config import LOG_PATH
from app.schemas.common import PortfolioParams
from app.schemas.paper import PaperCreateRequest
from app.services import paper_service
from app.services.account_store import load_account
from app.services.paper_service import trades_view


def test_replay_account_trades_through_the_recent_sessions(monkeypatch, tmp_path):
    log = tmp_path / "predictions_log.csv"
    shutil.copy(LOG_PATH, log)
    monkeypatch.setattr("app.services.live.LOG_PATH", log)
    params = PortfolioParams(top_fraction=0.2, min_score=0.0, sell_score=-0.1)
    paper_service.create_account(PaperCreateRequest(strategy="model", replay=True, params=params))
    account = load_account()
    assert account["replay"] is True
    assert len(account["equity"]) == paper_service.REPLAY_SESSIONS
    assert account["trades"] and account["last_date"] == account["equity"][-1]["date"]
    state = paper_service.read_state()
    assert state.account.replay and state.summary is not None and state.replay_start == account["start_date"]


def test_state_is_served_from_cache_after_the_first_read():
    paper_service.read_state()
    started = time.perf_counter()
    paper_service.read_state()
    assert time.perf_counter() - started < 0.3


def test_sell_reports_the_entry_it_closes():
    account = {"trades": [
        {"date": "2026-11-03", "symbol": "FPT", "side": "buy", "shares": 100, "price": 100.0, "value": 10_000_000.0, "fee": 15_000.0},
        {"date": "2026-11-05", "symbol": "FPT", "side": "sell", "shares": 100, "price": 110.0, "value": 11_000_000.0, "fee": 27_500.0},
    ]}
    sell, buy = trades_view(account)
    assert buy.pnl is None
    assert sell.entry_value == 10_000_000.0 and sell.entry_price == 100_000.0
    assert round(sell.pnl) == 957_500 and round(sell.pnl_pct, 4) == 0.0956
