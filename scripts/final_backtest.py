"""Final backtest of the chosen pooled model: baselines, random selection, fee sensitivity, drawdown."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from panel_experiments import (
    BUY_FEE, CONFIRM_START, MIN_HOLDINGS, RANDOM_STATE, SELL_FEE, STICKY_BUFFER, TRADING_DAYS,
    alpha_beta, alpha_interval, bootstrap_alpha_ci, top_k_portfolio,
)


ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_SYMBOLS = ("TCB", "CTG", "VNM", "ACB")
FEE_SCALES = (0.0, 0.5, 1.0, 2.0)
RANDOM_DRAWS = 200


def net_returns(book: pd.DataFrame, fee_scale: float) -> np.ndarray:
    cost = BUY_FEE * book["buy_turnover"] + SELL_FEE * book["sell_turnover"]
    return (book["gross"] - fee_scale * cost).to_numpy()


def max_drawdown(daily: np.ndarray) -> float:
    wealth = pd.Series(1.0 + daily).cumprod()
    return float((wealth / wealth.cummax() - 1.0).min())


def summarize(daily: np.ndarray, benchmark: np.ndarray, samples: np.ndarray | None = None) -> dict:
    """`samples` are bootstrap alpha draws when the caller already has them, to avoid resampling."""
    alpha, beta = alpha_beta(daily, benchmark, TRADING_DAYS)
    low, high = bootstrap_alpha_ci(daily, benchmark, TRADING_DAYS) if samples is None else alpha_interval(samples)
    return {
        "return_ann": daily.mean() * TRADING_DAYS, "total_return": float(np.prod(1.0 + daily) - 1.0),
        "sharpe": daily.mean() / daily.std() * np.sqrt(TRADING_DAYS), "max_drawdown": max_drawdown(daily),
        "alpha_ann": alpha, "alpha_ci_low": low, "alpha_ci_high": high, "beta": beta,
        "days": len(daily),
    }


def strategy_rows(frame: pd.DataFrame, period: str) -> list[dict]:
    daily_book = top_k_portfolio(frame)
    sticky_book = top_k_portfolio(frame, STICKY_BUFFER)
    benchmark = daily_book["benchmark"].to_numpy()
    rows = [{"period": period, "strategy": "equal_weight_universe", "fee_scale": 0.0,
             "turnover_per_day": 0.0, **summarize(benchmark, benchmark)}]
    for name, book in (("model_top20_daily", daily_book), ("model_top20_sticky", sticky_book)):
        for scale in FEE_SCALES:
            rows.append({"period": period, "strategy": name, "fee_scale": scale,
                         "turnover_per_day": book["buy_turnover"].mean(),
                         **summarize(net_returns(book, scale), benchmark)})
    return rows


def random_baseline(frame: pd.DataFrame, period: str, model_alpha: dict[float, float]) -> list[dict]:
    rng = np.random.default_rng(RANDOM_STATE)
    benchmark = None
    draws = {scale: [] for scale in FEE_SCALES}
    for _ in range(RANDOM_DRAWS):
        book = top_k_portfolio(frame.assign(score=rng.random(len(frame))))
        benchmark = book["benchmark"].to_numpy()
        for scale in FEE_SCALES:
            draws[scale].append(alpha_beta(net_returns(book, scale), benchmark, TRADING_DAYS)[0])
    return [
        {"period": period, "fee_scale": scale, "random_alpha_mean": np.mean(values),
         "random_alpha_std": np.std(values, ddof=1), "model_alpha": model_alpha[scale],
         "share_random_at_least_model": float(np.mean(np.array(values) >= model_alpha[scale]))}
        for scale, values in draws.items()
    ]


def buy_and_hold(frame: pd.DataFrame, period: str) -> list[dict]:
    returns = np.expm1(frame.pivot(index="time", columns="symbol", values="r_next"))
    rows = []
    for symbol in (*ORIGINAL_SYMBOLS, "ALL_19_EQUAL_WEIGHT_BUY_HOLD"):
        if symbol == "ALL_19_EQUAL_WEIGHT_BUY_HOLD":
            growth = (1.0 + returns.fillna(0.0)).prod()
            total = float(growth.mean() - 1.0)
            wealth = (1.0 + returns.fillna(0.0)).cumprod().mean(axis=1)
        else:
            total = float((1.0 + returns[symbol].dropna()).prod() - 1.0)
            wealth = (1.0 + returns[symbol].fillna(0.0)).cumprod()
        rows.append({"period": period, "asset": symbol, "total_return": total,
                     "max_drawdown": float((wealth / wealth.cummax() - 1.0).min()), "days": len(returns)})
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="pooled_abs_full")
    parser.add_argument("--model", default="ensemble3")
    parser.add_argument("--research-dir", type=Path, default=ROOT / "results" / "research")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    oof = pd.read_csv(args.research_dir / args.name / "oof.csv.gz", parse_dates=["time", "test_start"])
    frame = oof[oof["model"] == args.model].copy()
    frame["score"] = frame["p_up"] - frame["p_down"]
    periods = {
        "dev": frame[frame["test_start"] < CONFIRM_START], "confirm": frame[frame["test_start"] >= CONFIRM_START],
        "all": frame,
    }
    strategies, randoms, holdings = [], [], []
    for period, subset in periods.items():
        rows = strategy_rows(subset, period)
        strategies += rows
        model_alpha = {row["fee_scale"]: row["alpha_ann"] for row in rows if row["strategy"] == "model_top20_daily"}
        randoms += random_baseline(subset, period, model_alpha)
        holdings += buy_and_hold(subset, period)
    output_dir = args.research_dir / "final_backtest"
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {"strategies": pd.DataFrame(strategies), "random_baseline": pd.DataFrame(randoms),
              "buy_and_hold": pd.DataFrame(holdings)}
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
        print(f"\n{name}\n{table.round(3).to_string(index=False)}")
    print(f"\nminimum holdings {MIN_HOLDINGS}, fee buy {BUY_FEE:.4f}, sell {SELL_FEE:.4f}")


if __name__ == "__main__":
    main()
