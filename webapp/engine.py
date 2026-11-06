"""Long-only top-K portfolio simulation on daily score panels, with sticky holdings, T+2 lock and score threshold."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from market import ROOT  # noqa: F401  (puts scripts/ on sys.path)
from final_backtest import FEE_SCALES, net_returns, summarize  # noqa: E402
from panel_experiments import (  # noqa: E402
    MIN_HOLDINGS, RANDOM_STATE, TOP_FRACTION, TRADING_DAYS, bootstrap_alpha_ci,
)

RANDOM_DRAWS = 30


@dataclass(frozen=True)
class Params:
    top_fraction: float = TOP_FRACTION
    buffer: float = 1.0
    min_hold: int = 1
    min_score: float = -np.inf


@dataclass
class Constraints:
    """Per-signal-date execution limits: price limit locks and the largest tradable weight per name."""

    buy_blocked: pd.DataFrame | None = None
    sell_blocked: pd.DataFrame | None = None
    capacity: pd.DataFrame | None = None


def net(book: pd.DataFrame, fee_scale: float, slippage_bps: float = 0.0) -> np.ndarray:
    return net_returns(book, fee_scale) - slippage_bps / 1e4 * (book["buy_turnover"] + book["sell_turnover"]).to_numpy()


def select_step(
    score: np.ndarray, held: dict[int, int], params: Params,
    buy_blocked: np.ndarray | None = None, sell_blocked: np.ndarray | None = None,
) -> tuple[list[int], int]:
    """Pick holdings for one session. `held` maps symbol index to sessions held so far; returns (selected, target).

    Names stuck at the price limit cannot be bought (skipped) or sold (kept)."""
    valid = ~np.isnan(score)
    count = int(valid.sum())
    if count == 0:
        return [], 0
    target = max(MIN_HOLDINGS, int(round(count * params.top_fraction)))
    order = np.argsort(-np.where(valid, score, -np.inf), kind="stable")
    rank = np.full(len(score), np.inf)
    rank[order[:count]] = np.arange(1, count + 1)
    locked = [s for s, age in held.items() if age < params.min_hold or (sell_blocked is not None and sell_blocked[s])]
    keep = sorted(
        (s for s in held if s not in locked and rank[s] <= params.buffer * target and score[s] >= params.min_score),
        key=lambda s: rank[s],
    )
    keep = (locked + keep)[: max(target, len(locked))]
    entrants = [int(s) for s in order[:count] if s not in keep and score[s] >= params.min_score
                and not (buy_blocked is not None and buy_blocked[s])]
    return keep + entrants[: max(target - len(keep), 0)], target


def simulate(
    score: pd.DataFrame, returns: pd.DataFrame, params: Params, constraints: Constraints | None = None
) -> pd.DataFrame:
    constraints = constraints or Constraints()

    def aligned(frame: pd.DataFrame | None, fill: float) -> np.ndarray | None:
        return None if frame is None else frame.reindex(index=score.index, columns=score.columns).fillna(fill).to_numpy()

    buy_blocked, sell_blocked = aligned(constraints.buy_blocked, False), aligned(constraints.sell_blocked, False)
    capacity = aligned(constraints.capacity, np.inf)
    scores = score.to_numpy(dtype=float)
    daily = returns.reindex(index=score.index, columns=score.columns).fillna(0.0).to_numpy()
    held: dict[int, int] = {}
    previous = np.zeros(scores.shape[1])
    rows = []
    for t in range(len(scores)):
        selected, target = select_step(
            scores[t], held, params,
            None if buy_blocked is None else buy_blocked[t].astype(bool),
            None if sell_blocked is None else sell_blocked[t].astype(bool),
        )
        weights = np.zeros_like(previous)
        if selected:
            weights[selected] = 1.0 / max(target, len(selected))
            if capacity is not None:
                weights = np.minimum(weights, capacity[t])
        change = weights - previous
        rows.append((weights @ daily[t], np.clip(change, 0, None).sum(), np.clip(-change, 0, None).sum(), len(selected)))
        held = {s: held.get(s, 0) + 1 for s in selected}
        previous = weights
    return pd.DataFrame(rows, index=score.index, columns=["gross", "buy_turnover", "sell_turnover", "holdings"])


def benchmark_returns(returns: pd.DataFrame, index: pd.Index) -> pd.Series:
    return returns.reindex(index).mean(axis=1)


def evaluate(book: pd.DataFrame, benchmark: pd.Series, fee_scale: float, slippage_bps: float = 0.0,
             trials: int = 1) -> dict:
    """`trials` widens the alpha interval to a Bonferroni level for the number of strategies tried."""
    daily = net(book, fee_scale, slippage_bps)
    if daily.std() == 0:
        return {"return_ann": 0.0, "total_return": 0.0, "sharpe": np.nan, "max_drawdown": 0.0, "alpha_ann": 0.0,
                "alpha_ci_low": np.nan, "alpha_ci_high": np.nan, "alpha_adj_low": np.nan, "alpha_adj_high": np.nan,
                "beta": 0.0, "days": len(daily), "turnover_per_day": 0.0, "avg_holdings": 0.0}
    adjusted = bootstrap_alpha_ci(daily, benchmark.to_numpy(), TRADING_DAYS, 1 - 0.05 / trials)
    return {**summarize(daily, benchmark.to_numpy()), "alpha_adj_low": adjusted[0], "alpha_adj_high": adjusted[1],
            "turnover_per_day": float(book["buy_turnover"].mean()), "avg_holdings": float(book["holdings"].mean())}


def random_selection(returns: pd.DataFrame, availability: pd.DataFrame, params: Params, fee_scale: float,
                     slippage_bps: float = 0.0, constraints: Constraints | None = None) -> dict:
    """Median over random-score portfolios sharing the real score availability pattern."""
    rng = np.random.default_rng(RANDOM_STATE)
    benchmark = benchmark_returns(returns, availability.index)
    rows = []
    for _ in range(RANDOM_DRAWS):
        noise = pd.DataFrame(rng.random(availability.shape), index=availability.index, columns=availability.columns)
        noise = noise.where(availability.notna())
        book = simulate(noise, returns, params, constraints)
        daily = net(book, fee_scale, slippage_bps)
        rows.append({"return_ann": daily.mean() * TRADING_DAYS, "sharpe": daily.mean() / daily.std() * np.sqrt(TRADING_DAYS),
                     "total_return": float(np.prod(1.0 + daily) - 1.0)})
    return pd.DataFrame(rows).median().to_dict() | {"alpha_ann": np.nan, "beta": np.nan}


__all__ = ["FEE_SCALES", "Constraints", "Params", "benchmark_returns", "evaluate", "net", "random_selection",
           "select_step", "simulate"]
