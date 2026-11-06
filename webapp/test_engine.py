"""Self-check: the engine must reproduce panel_experiments.top_k_portfolio when no T+2 lock or threshold is used."""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine import Constraints, Params, net, select_step, simulate
from market import limit_band
from panel_experiments import top_k_portfolio


def synthetic_frame(days: int = 120, symbols: int = 19, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=days)
    frame = pd.DataFrame(
        [(d, f"S{i:02d}", rng.normal(), rng.normal(0, 0.02)) for d in dates for i in range(symbols)],
        columns=["time", "symbol", "score", "r_next"],
    )
    frame.loc[rng.random(len(frame)) < 0.05, "score"] = np.nan
    return frame.dropna(subset=["score"])


def test_matches_top_k_portfolio():
    frame = synthetic_frame()
    score = frame.pivot(index="time", columns="symbol", values="score")
    returns = np.expm1(frame.pivot(index="time", columns="symbol", values="r_next"))
    for buffer in (1.0, 2.0):
        expected = top_k_portfolio(frame, buffer)
        book = simulate(score, returns, Params(buffer=buffer))
        for column in ("gross", "buy_turnover", "sell_turnover"):
            assert np.allclose(book[column], expected[column]), (buffer, column)


def test_min_hold_locks_positions():
    score = np.array([3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.0])
    params = Params(top_fraction=0.3, min_hold=2)
    selected, target = select_step(score, {9: 1}, params)
    assert 9 in selected and target == 3 and len(selected) == 3
    assert 9 not in select_step(score, {9: 2}, params)[0]


def test_threshold_leaves_cash():
    score = np.array([0.5, 0.1, -0.2, -0.3, -0.4, -0.5])
    selected, target = select_step(score, {}, Params(min_score=0.0))
    assert selected == [0, 1] and target == 3


def test_price_limits_block_orders():
    score = np.array([3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.0])
    params = Params(top_fraction=0.3)
    buy_blocked = np.zeros(10, dtype=bool)
    buy_blocked[0] = True
    assert 0 not in select_step(score, {}, params, buy_blocked)[0]
    sell_blocked = np.zeros(10, dtype=bool)
    sell_blocked[9] = True
    assert 9 in select_step(score, {9: 5}, params, None, sell_blocked)[0]


def test_capacity_caps_weight_and_slippage_costs():
    frame = synthetic_frame(days=30)
    score = frame.pivot(index="time", columns="symbol", values="score")
    returns = np.expm1(frame.pivot(index="time", columns="symbol", values="r_next"))
    capped = simulate(score, returns, Params(), Constraints(capacity=score * 0 + 0.05))
    assert (capped["buy_turnover"] <= 0.05 * capped["holdings"] + 1e-9).all()
    book = simulate(score, returns, Params())
    assert (net(book, 1.0, 10.0) < net(book, 1.0, 0.0)).all()


def test_limit_band_uses_tick_size():
    ceiling, floor = limit_band(np.array([9.0, 20.0, 100.0]))
    assert np.allclose(ceiling, [9.63, 21.4, 107.0]) and np.allclose(floor, [8.37, 18.6, 93.0])


if __name__ == "__main__":
    for name, function in list(globals().items()):
        if name.startswith("test_"):
            function()
            print(f"{name} ok")
