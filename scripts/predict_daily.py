"""Score the latest closed daily candles with the saved pooled ensemble3 and update the paper-trading log."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost

from clean_data import clean_daily_data
from crawl import VN, fetch
from panel_data import MIN_SYMBOLS_PER_DATE, featurize
from panel_experiments import MIN_HOLDINGS, STICKY_BUFFER, TOP_FRACTION, sticky_selection
from train_final_model import ensemble_probabilities, load_bundle


ROOT = Path(__file__).resolve().parent.parent
CANDLE_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
MIN_HISTORY = 250
MAX_MODEL_AGE_DAYS = 100
MAX_DATA_AGE_DAYS = 4
LIVE_VERSIONS = {"scikit_learn": sklearn.__version__, "xgboost": xgboost.__version__, "numpy": np.__version__,
                 "pandas": pd.__version__}


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def crawl_universe(symbols: list[str], data_dir: Path, days: int) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    end = datetime.now(VN)
    for symbol in symbols:
        rows = fetch(symbol, "1D", end - timedelta(days=days), end)
        pd.DataFrame(rows, columns=CANDLE_COLUMNS).to_csv(data_dir / f"{symbol}.csv", index=False)
        print(f"crawled {symbol}: {len(rows)} candles, last {rows[-1][0]}")


def load_cleaned_universe(symbols: list[str], data_dir: Path) -> dict[str, pd.DataFrame]:
    universe = {}
    for symbol in symbols:
        cleaned, _ = clean_daily_data(pd.read_csv(data_dir / f"{symbol}.csv"))
        cleaned["time"] = pd.to_datetime(cleaned["time"])
        universe[symbol] = cleaned.sort_values("time").reset_index(drop=True)
        if len(cleaned) < MIN_HISTORY:
            warn(f"{symbol} has only {len(cleaned)} closed candles, fewer than {MIN_HISTORY}")
    return universe


def check_model(metadata: dict, target_date: pd.Timestamp) -> None:
    for name, version in LIVE_VERSIONS.items():
        if metadata["versions"][name] != version:
            warn(f"{name} is {version} but the model was saved with {metadata['versions'][name]}")
    age = (target_date - pd.Timestamp(metadata["trained_until"])).days
    if age > MAX_MODEL_AGE_DAYS:
        warn(f"model was trained {age} days before {target_date.date()}; retrain with train_final_model.py")


def score_latest(bundle: dict, universe: dict[str, pd.DataFrame], days: int) -> pd.DataFrame:
    columns = bundle["metadata"]["feature_columns"]
    features = featurize(universe).replace([np.inf, -np.inf], np.nan).dropna(subset=columns)
    features = features[features.groupby("time")["symbol"].transform("size") >= MIN_SYMBOLS_PER_DATE]
    dates = np.sort(features["time"].unique())[-days:]
    frame = features[features["time"].isin(dates)]
    scored = frame[["time", "symbol"]].join(ensemble_probabilities(bundle, frame))
    by_date = scored.groupby("time")
    scored["rank"] = by_date["score"].rank(ascending=False, method="first").astype(int)
    scored["n_symbols"] = by_date["symbol"].transform("size")
    scored["model_trained_until"] = bundle["metadata"]["trained_until"]
    scored["scored_at"] = datetime.now(VN).isoformat(timespec="seconds")
    return scored.sort_values(["time", "rank"]).reset_index(drop=True)


def update_log(path: Path, scored: pd.DataFrame) -> pd.DataFrame:
    if path.is_file():
        previous = pd.read_csv(path, parse_dates=["time"])
        scored = pd.concat([previous[~previous["time"].isin(scored["time"])], scored], ignore_index=True)
    log = scored.sort_values(["time", "rank"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    log.to_csv(path, index=False)
    return log


def portfolio_selection(log: pd.DataFrame, buffer: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = log.pivot(index="time", columns="symbol", values="score")
    rank = scores.rank(axis=1, ascending=False, method="first")
    holdings = np.maximum(MIN_HOLDINGS, (scores.notna().sum(axis=1) * TOP_FRACTION).round().astype(int))
    daily = rank.le(holdings, axis=0) & scores.notna()
    sticky = sticky_selection(rank, holdings, buffer) & scores.notna()
    return daily, sticky


def latest_signals(log: pd.DataFrame, buffer: float) -> pd.DataFrame:
    daily, sticky = portfolio_selection(log, buffer)
    date = log["time"].max()
    previous = sticky.iloc[-2] if len(sticky) > 1 else pd.Series(False, index=sticky.columns)
    signals = log[log["time"] == date].set_index("symbol")
    signals["daily_top"] = daily.loc[date].reindex(signals.index)
    signals["sticky_hold"] = sticky.loc[date].reindex(signals.index)
    held_before = previous.reindex(signals.index).fillna(False).astype(bool)
    signals["sticky_action"] = np.select(
        [signals["sticky_hold"] & ~held_before, ~signals["sticky_hold"] & held_before, signals["sticky_hold"]],
        ["buy", "sell", "hold"], default="",
    )
    return signals.drop(columns=["model_trained_until", "scored_at"]).reset_index()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models" / "ensemble3_pooled_1D")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "live" / "raw" / "1D")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "live")
    parser.add_argument("--crawl", action="store_true")
    parser.add_argument("--crawl-days", type=int, default=420)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--buffer", type=float, default=STICKY_BUFFER)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = load_bundle(args.model_dir)
    symbols = bundle["metadata"]["symbols"]
    if args.crawl:
        crawl_universe(symbols, args.data_dir, args.crawl_days)
    universe = load_cleaned_universe(symbols, args.data_dir)
    scored = score_latest(bundle, universe, args.days)
    target_date = scored["time"].max()
    check_model(bundle["metadata"], target_date)
    missing = sorted(set(symbols) - set(scored.loc[scored["time"] == target_date, "symbol"]))
    if missing:
        warn(f"no features on {target_date.date()} for {', '.join(missing)}; market features use the other symbols")
    if (datetime.now(VN).date() - target_date.date()).days > MAX_DATA_AGE_DAYS:
        warn(f"latest candle {target_date.date()} is more than {MAX_DATA_AGE_DAYS} days old")

    log = update_log(args.output_dir / "predictions_log.csv", scored)
    signals = latest_signals(log, args.buffer)
    signals.to_csv(args.output_dir / "latest_signals.csv", index=False)
    pd.set_option("display.width", 200)
    print(f"\nsignals from the close of {target_date.date()} (trade at the next session):")
    print(signals.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
