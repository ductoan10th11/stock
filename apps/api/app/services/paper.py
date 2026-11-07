"""Paper-trading account: orders fill at the next session's open, lot size 100, repo fee model."""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from app.services.engine import Params, select_step, size_weights
from app.services.market import ADV_PARTICIPATION, PRICE_UNIT, Prices, adv_shares, limit_band
from panel_experiments import BUY_FEE, SELL_FEE

LOT_SIZE = 100
DEFAULT_SLIPPAGE_BPS = 10.0


def new_account(weights: dict[str, float], params: Params, capital: float, start_date: str,
                slippage_bps: float = DEFAULT_SLIPPAGE_BPS) -> dict:
    return {
        "weights": weights, "slippage_bps": slippage_bps, "params": {**asdict(params), "min_score": None if np.isinf(params.min_score) else params.min_score},
        "initial_capital": capital, "start_date": start_date, "last_date": start_date, "cash": capital, "replay": False,
        "positions": {}, "trades": [], "equity": [],
    }


def account_params(account: dict) -> Params:
    raw = account["params"]
    return Params(**{**raw, "min_score": -np.inf if raw["min_score"] is None else raw["min_score"]})


def _plan(account: dict, score_row: pd.Series, buy_blocked: pd.Series | None = None,
          sell_blocked: pd.Series | None = None) -> tuple[list[str], int, dict[str, float]]:
    symbols = list(score_row.index)
    held = {symbols.index(s): p["held"] for s, p in account["positions"].items() if s in symbols}
    as_array = lambda flags: None if flags is None else flags.reindex(symbols).fillna(False).to_numpy(dtype=bool)  # noqa: E731
    params, scores = account_params(account), score_row.to_numpy(dtype=float)
    selected, target = select_step(scores, held, params, as_array(buy_blocked), as_array(sell_blocked))
    chosen = [symbols[i] for i in selected]
    return chosen, target, dict(zip(chosen, size_weights(scores[selected], target, params.sizing)))


def _trade(account: dict, date: pd.Timestamp, symbol: str, side: str, shares: int, price: float) -> None:
    value = shares * price * PRICE_UNIT
    fee = value * (BUY_FEE if side == "buy" else SELL_FEE)
    account["cash"] += -(value + fee) if side == "buy" else value - fee
    account["trades"].append({"date": str(date.date()), "symbol": symbol, "side": side, "shares": shares,
                              "price": price, "value": value, "fee": fee})


def lot_cap(adv: float) -> int:
    return int(ADV_PARTICIPATION * adv // LOT_SIZE * LOT_SIZE) if adv == adv else 10**12


def advance(account: dict, score: pd.DataFrame, prices: Prices) -> int:
    """Process every session after `last_date` that has candles; returns the number of sessions processed."""
    open_, close = prices.open, prices.close.ffill()
    adv = adv_shares(prices)
    slip = account.get("slippage_bps", 0.0) / 1e4
    sessions = close.index[close.index > pd.Timestamp(account["last_date"])]
    for date in sessions:
        previous = close.index[close.index < date][-1]
        if previous in score.index and score.loc[previous].notna().any():
            positions = account["positions"]
            day_open = open_.loc[date]
            ceiling, floor = limit_band(close.loc[previous])
            selected, _, weights = _plan(account, score.loc[previous], day_open >= ceiling - 1e-6, day_open <= floor + 1e-6)
            marked = day_open.fillna(close.loc[previous])
            equity_open = account["cash"] + sum(p["shares"] * marked[s] * PRICE_UNIT for s, p in positions.items())
            for symbol in [s for s in positions if s not in selected and not np.isnan(day_open.get(s, np.nan))]:
                _trade(account, date, symbol, "sell", positions.pop(symbol)["shares"], float(day_open[symbol]) * (1 - slip))
            for symbol in (s for s in selected if s not in positions):
                price = day_open.get(symbol, np.nan) * (1 + slip)
                if np.isnan(price):
                    continue
                spend = min(equity_open * weights[symbol], account["cash"]) / (1 + BUY_FEE)
                shares = int(spend // (price * PRICE_UNIT) // LOT_SIZE * LOT_SIZE)
                shares = min(shares, lot_cap(adv.loc[previous, symbol]))
                if shares > 0:
                    _trade(account, date, symbol, "buy", shares, float(price))
                    positions[symbol] = {"shares": shares, "held": 0, "cost": float(price)}
            for position in positions.values():
                position["held"] += 1
        value = sum(p["shares"] * close.loc[date, s] * PRICE_UNIT for s, p in account["positions"].items())
        account["equity"].append({"date": str(date.date()), "cash": account["cash"], "value": value,
                                  "equity": account["cash"] + value})
        account["last_date"] = str(date.date())
    return len(sessions)


def next_orders(account: dict, score: pd.DataFrame, prices: Prices) -> pd.DataFrame:
    """Orders the strategy would place for the next session, sized at the latest close."""
    close = prices.close
    last = close.index[-1]
    if last not in score.index or score.loc[last].isna().all():
        return pd.DataFrame(columns=["symbol", "action", "shares", "est_price"])
    selected, _, weights = _plan(account, score.loc[last])
    last_close = close.ffill().iloc[-1]
    held = account["positions"]
    equity = account["cash"] + sum(p["shares"] * last_close[s] * PRICE_UNIT for s, p in held.items())
    rows = [{"symbol": s, "action": "sell", "shares": p["shares"], "est_price": last_close[s]}
            for s, p in held.items() if s not in selected]
    rows += [{"symbol": s, "action": "hold", "shares": held[s]["shares"], "est_price": last_close[s]}
             for s in selected if s in held]
    adv = adv_shares(prices).iloc[-1]
    rows += [{"symbol": s, "action": "buy",
              "shares": min(int(equity * weights[s] // (last_close[s] * PRICE_UNIT) // LOT_SIZE * LOT_SIZE), lot_cap(adv[s])),
              "est_price": last_close[s]} for s in selected if s not in held]
    return pd.DataFrame(rows, columns=["symbol", "action", "shares", "est_price"])
