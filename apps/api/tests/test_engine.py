"""Self-check: the engine must reproduce panel_experiments.top_k_portfolio when no T+2 lock or threshold is used."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.engine import Constraints, Params, entry_weights, net, select_step, simulate, size_weights
from app.services.market import limit_band
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



def test_score_sizing_splits_in_proportion_and_keeps_total_exposure():
    scores = np.array([0.3, 0.1, 0.05, 0.05])
    weights = size_weights(scores, 4, "score")
    assert np.allclose(weights, scores / scores.sum()) and np.isclose(weights.sum(), 1.0)
    one_of_four = size_weights(np.array([0.2]), 4, "score")
    assert np.allclose(one_of_four, [0.25]) and np.allclose(size_weights(np.array([0.2]), 4, "equal"), [0.25])
    assert np.allclose(size_weights(scores, 4, "equal"), 0.25)


def test_score_sizing_never_selects_or_funds_a_non_positive_score():
    score = np.array([0.044, -0.010, -0.015, -0.022, -0.039, -0.1, -0.2, -0.3, -0.4, -0.5])
    params = Params(top_fraction=0.4, sizing="score")
    selected, target = select_step(score, {}, params)
    assert selected == [0] and target == 4
    assert np.allclose(size_weights(np.array([0.5, -0.2]), 4, "score"), [0.5, 0.0])
    assert select_step(score, {}, Params(top_fraction=0.4, min_score=0.0))[0] == [0]


def test_entry_weights_keep_held_names_and_fund_entrants_from_free_capital():
    scores = np.array([0.3, 0.1, 0.1, 0.0, 0.0])
    previous = np.array([0.4, 0.0, 0.0, 0.0, 0.0])
    weights = entry_weights(scores, [0, 1, 2], previous, 3)
    assert np.allclose(weights[:3], [0.4, 0.2, 0.2]) and weights[3:].sum() == 0
    crowded = entry_weights(scores, [0, 1], np.array([0.9, 0.0, 0.0, 0.0, 0.0]), 3)
    assert np.isclose(crowded.sum(), 1.0) and np.isclose(crowded[1], 0.1)


def test_score_sizing_is_not_re_sized_after_entry():
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2024-01-01", periods=30)
    scores = pd.DataFrame(np.tile(rng.uniform(0.05, 0.5, 12), (30, 1)), index=dates, columns=[f"S{i:02d}" for i in range(12)])
    returns = pd.DataFrame(rng.normal(0, 0.02, scores.shape), index=dates, columns=scores.columns)
    book = simulate(scores, returns, Params(sizing="score"))
    assert book["buy_turnover"].iloc[0] > 0 and (book["buy_turnover"].iloc[1:] == 0).all()
    assert np.isclose(book["buy_turnover"].iloc[0], 1.0)


def test_sell_score_exits_on_the_signal_not_on_the_ranking():
    held = {9: 5}
    low_rank_but_positive = np.array([3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6, 0.5, 0.4, 0.2])
    by_rank = select_step(low_rank_but_positive, held, Params(top_fraction=0.3, buffer=1.0))[0]
    by_signal = select_step(low_rank_but_positive, held, Params(top_fraction=0.3, buffer=1.0, sell_score=0.0))[0]
    assert 9 not in by_rank and 9 in by_signal
    turned_bad = low_rank_but_positive.copy()
    turned_bad[9] = -0.3
    assert 9 not in select_step(turned_bad, held, Params(top_fraction=0.3, sell_score=-0.1))[0]
    assert 9 in select_step(turned_bad, held, Params(top_fraction=0.3, sell_score=-0.5))[0]


def test_signal_exit_trades_far_less_than_rank_exit_on_noisy_scores():
    rng = np.random.default_rng(3)
    dates = pd.bdate_range("2024-01-01", periods=120)
    symbols = [f"S{i:02d}" for i in range(19)]
    scores = pd.DataFrame(rng.normal(0.05, 0.1, (120, 19)), index=dates, columns=symbols)
    returns = pd.DataFrame(rng.normal(0, 0.02, scores.shape), index=dates, columns=symbols)
    by_rank = simulate(scores, returns, Params(top_fraction=0.2, buffer=2.0, min_hold=2, min_score=0.0))
    by_signal = simulate(scores, returns, Params(top_fraction=0.2, min_hold=2, min_score=0.0, sell_score=-0.2))
    assert by_signal["buy_turnover"].mean() < by_rank["buy_turnover"].mean() / 3


def test_nothing_selected_is_a_valid_state_for_sizing_and_the_paper_plan():
    import pandas as pd

    from app.services.paper import _plan, new_account

    assert size_weights(np.array([]), 3, "equal").size == 0 and size_weights(np.array([]), 3, "score").size == 0
    symbols = [f"S{i:02d}" for i in range(10)]
    account = new_account({"model": 1.0}, Params(top_fraction=0.3, min_score=0.06, sell_score=-0.1), 1e9, "2026-11-06")
    selected, target, weights = _plan(account, pd.Series(np.linspace(0.04, -0.2, 10), index=symbols))
    assert selected == [] and target == 3 and weights == {}
