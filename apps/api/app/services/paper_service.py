"""Paper-trading account use cases: read state, create, delete and refresh with new candles."""

from __future__ import annotations

import threading

import pandas as pd

from app.core.config import INDEX_PATH
from app.core.errors import PaperError
from app.schemas.common import PortfolioParams
from app.schemas.paper import (
    AccountInfo, EquityCurve, Order, PaperCreateRequest, PaperState, Position, RankingRow, Summary, Trade,
)
from app.services.backtest import plain
from app.services.catalog import BLEND, MODEL
from app.services.live import (
    cached_prices, cached_score, cached_universe, live_score, refresh_live, score_recent, trained_until,
)
from app.services.market import PRICE_UNIT
from app.services.account_store import delete_account as delete_stored_account, load_account, save_account
from app.services.paper import advance, new_account, next_orders

_lock = threading.Lock()
REPLAY_SESSIONS = 5


def account_info(account: dict) -> AccountInfo:
    return AccountInfo(
        id=account["id"], replay=account["replay"], weights=account["weights"], params=PortfolioParams(**account["params"]), initial_capital=account["initial_capital"],
        slippage_bps=account["slippage_bps"], start_date=account["start_date"], last_date=account["last_date"],
    )


def equity_view(account: dict, prices) -> tuple[Summary, EquityCurve] | None:
    if not account["equity"]:
        return None
    equity = pd.DataFrame(account["equity"]).assign(date=lambda frame: pd.to_datetime(frame["date"])).set_index("date")
    benchmark = prices.close.pct_change().mean(axis=1).loc[equity.index].add(1).cumprod()
    vnindex = None
    if INDEX_PATH.is_file():
        closes = pd.read_csv(INDEX_PATH, parse_dates=["time"]).set_index("time")["close"]
        vnindex = closes.pct_change().reindex(equity.index).fillna(0.0).add(1).cumprod()
    last, capital = equity.iloc[-1], account["initial_capital"]
    summary = Summary(
        equity=last["equity"], cash=last["cash"], gain=last["equity"] - capital, gain_pct=last["equity"] / capital - 1,
        cash_pct=last["cash"] / last["equity"], equal_weight_return=benchmark.iloc[-1] - 1,
        vnindex_return=None if vnindex is None else vnindex.iloc[-1] - 1,
    )
    curve = EquityCurve(
        dates=[f"{date:%Y-%m-%d}" for date in equity.index], account=(equity["equity"] / capital).tolist(),
        equal_weight=benchmark.tolist(), vnindex=None if vnindex is None else vnindex.tolist(),
    )
    return summary, curve


def read_state() -> PaperState:
    prices, account = cached_prices(), load_account()
    base = {"trained_until": f"{trained_until():%Y-%m-%d}", "account": None if account is None else account_info(account)}
    if prices is None:
        return PaperState(data_ready=False, **base)
    latest = prices.close.index[-1]
    base |= {"data_ready": True, "latest_candle": f"{latest:%Y-%m-%d}", "replay_start": f"{prices.close.index[-REPLAY_SESSIONS - 1]:%Y-%m-%d}"}
    if account is None:
        return PaperState(**base)

    score = cached_score(account["weights"])
    if score.empty:
        return PaperState(**base, trades=trades_view(account))
    signal_date = score.dropna(how="all").index.max()
    summary, curve = equity_view(account, prices) or (None, None)
    last_close = prices.close.ffill().iloc[-1]
    orders = next_orders(account, score, prices)
    ranking = score.loc[signal_date].dropna().sort_values(ascending=False)
    return PaperState(
        **base, score_ready=True, signal_date=f"{signal_date:%Y-%m-%d}",
        summary=summary, equity=curve,
        orders=[Order(symbol=r.symbol, action=r.action, shares=int(r.shares), price=float(r.est_price) * PRICE_UNIT,
                      value=float(r.shares * r.est_price) * PRICE_UNIT) for r in orders.itertuples()],
        positions=[Position(symbol=symbol, shares=p["shares"], cost=p["cost"] * PRICE_UNIT, price=last_close[symbol] * PRICE_UNIT,
                            pnl_pct=last_close[symbol] / p["cost"] - 1, value=p["shares"] * last_close[symbol] * PRICE_UNIT,
                            held=p["held"]) for symbol, p in account["positions"].items()],
        ranking=[RankingRow(rank=rank, symbol=symbol, score=value, held=symbol in account["positions"])
                 for rank, (symbol, value) in enumerate(ranking.items(), start=1)],
        trades=trades_view(account),
    )


def trades_view(account: dict) -> list[Trade]:
    """Newest first. A sell carries the entry it closes; positions are always sold whole, so one open entry per symbol."""
    entries: dict[str, dict] = {}
    rows = []
    for trade in account["trades"]:
        extra = {}
        if trade["side"] == "buy":
            entries[trade["symbol"]] = trade
        elif trade["symbol"] in entries:
            entry = entries.pop(trade["symbol"])
            cost = entry["value"] + entry["fee"]
            pnl = trade["value"] - trade["fee"] - cost
            extra = {"entry_price": entry["price"] * PRICE_UNIT, "entry_value": entry["value"], "pnl": pnl, "pnl_pct": pnl / cost}
        rows.append(Trade(**{**trade, "price": trade["price"] * PRICE_UNIT}, **extra))
    return rows[::-1]


def create_account(request: PaperCreateRequest) -> None:
    weights = request.blend_weights if request.strategy == BLEND else {request.strategy: 1.0}
    with _lock:
        if load_account() is not None:
            raise PaperError("account_exists")
        prices = cached_prices()
        if prices is None:
            raise PaperError("no_live_data")
        latest = prices.close.index[-1]
        if weights.get(MODEL) and latest <= trained_until() and not request.replay:
            raise PaperError("model_not_ahead")
        params = request.params.to_engine()
        params = params if weights == {MODEL: 1.0} else plain(params)
        if not request.replay:
            save_account(new_account(weights, params, request.capital, str(latest.date()), request.slippage_bps))
            return
        start = prices.close.index[-REPLAY_SESSIONS - 1]
        score_recent(REPLAY_SESSIONS + 3)
        account = new_account(weights, params, request.capital, str(start.date()), request.slippage_bps)
        account["replay"] = True
        advance(account, live_score(cached_universe(), weights, in_sample=True), cached_prices())
        save_account(account)


def delete_account() -> None:
    with _lock:
        account = load_account()
        if account:
            delete_stored_account(account["id"])


def refresh() -> int:
    with _lock:
        refresh_live()
        account = load_account()
        if account is None:
            return 0
        sessions = advance(account, cached_score(account["weights"]), cached_prices())
        save_account(account)
        return sessions
