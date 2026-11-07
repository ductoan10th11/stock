"""Live data for paper trading: refresh candles, score them with the saved model, load the scored universe."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import cache, lru_cache

import pandas as pd

from app.core.config import INDEX_PATH, LIVE_DIR, LOG_PATH, MODEL_DIR
from app.services.market import Prices, alpha_scores, blend, wide_prices
from crawl import VN, fetch
from predict_daily import CANDLE_COLUMNS, crawl_universe, load_cleaned_universe, score_latest, update_log
from train_final_model import load_bundle

CRAWL_DAYS = 700
MIN_SCORED_DAYS = 5


@cache
def model_metadata() -> dict:
    return json.loads((MODEL_DIR / "metadata.json").read_text())


def trained_until() -> pd.Timestamp:
    return pd.Timestamp(model_metadata()["trained_until"])


def load_live() -> dict[str, pd.DataFrame] | None:
    symbols = model_metadata()["symbols"]
    if not all((LIVE_DIR / f"{symbol}.csv").is_file() for symbol in symbols):
        return None
    return load_cleaned_universe(symbols, LIVE_DIR)


def refresh_live() -> None:
    bundle = load_bundle(MODEL_DIR)
    symbols = bundle["metadata"]["symbols"]
    crawl_universe(symbols, LIVE_DIR, CRAWL_DAYS)
    end = datetime.now(VN)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fetch("VNINDEX", "1D", end - timedelta(days=CRAWL_DAYS), end, "index"), columns=CANDLE_COLUMNS).to_csv(
        INDEX_PATH, index=False)
    universe = load_cleaned_universe(symbols, LIVE_DIR)
    last_logged = pd.read_csv(LOG_PATH, parse_dates=["time"])["time"].max() if LOG_PATH.is_file() else None
    latest = max(frame["time"].max() for frame in universe.values())
    days = MIN_SCORED_DAYS if last_logged is None else max(MIN_SCORED_DAYS, (latest - last_logged).days + 3)
    update_log(LOG_PATH, score_latest(bundle, universe, days))


def score_recent(days: int) -> None:
    bundle = load_bundle(MODEL_DIR)
    universe = load_cleaned_universe(bundle["metadata"]["symbols"], LIVE_DIR)
    update_log(LOG_PATH, score_latest(bundle, universe, days))


def live_score(universe: dict, weights: dict[str, float], in_sample: bool = False) -> pd.DataFrame:
    """Model scores count only after the training cutoff; earlier dates are in-sample (kept only for a replay)."""
    signals = alpha_scores(universe)
    reference = signals["low_volatility"]
    if LOG_PATH.is_file():
        model = pd.read_csv(LOG_PATH, parse_dates=["time"]).pivot(index="time", columns="symbol", values="score")
        model = model if in_sample else model[model.index > trained_until()]
        signals["model"] = model.reindex(index=reference.index, columns=reference.columns)
    if weights.get("model") and "model" not in signals:
        return pd.DataFrame()
    return blend(signals, weights)


def data_stamp() -> tuple[int, ...]:
    paths = [*sorted(LIVE_DIR.glob("*.csv")), LOG_PATH]
    return tuple(path.stat().st_mtime_ns if path.exists() else 0 for path in paths)


@lru_cache(maxsize=2)
def _universe(stamp: tuple[int, ...]) -> dict[str, pd.DataFrame] | None:
    return load_live()


@lru_cache(maxsize=2)
def _prices(stamp: tuple[int, ...]) -> Prices | None:
    universe = _universe(stamp)
    return None if universe is None else wide_prices(universe)


@lru_cache(maxsize=4)
def _score(weights: tuple[tuple[str, float], ...], stamp: tuple[int, ...]) -> pd.DataFrame:
    return live_score(_universe(stamp), dict(weights))


def cached_universe() -> dict[str, pd.DataFrame] | None:
    """Loading and scoring the 19 symbols takes about a second; the result only changes when a data file does."""
    return _universe(data_stamp())


def cached_prices() -> Prices | None:
    return _prices(data_stamp())


def cached_score(weights: dict[str, float]) -> pd.DataFrame:
    return _score(tuple(sorted(weights.items())), data_stamp())
