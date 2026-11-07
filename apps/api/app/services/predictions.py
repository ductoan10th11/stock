"""Per-day model predictions for the chart: out-of-fold history, then live scores after the training cutoff."""

from __future__ import annotations

from functools import cache

import numpy as np
import pandas as pd

from app.core.config import LIVE_DIR, LOG_PATH, OOF_PATH
from app.schemas.predictions import (
    Candle, DailyPrediction, HitRate, LatestPredictions, PredictionRow, SymbolPredictions,
)
from app.services.live import model_metadata, trained_until
from app.services.market import MODEL_NAME
from panel_data import THRESHOLD
from predict_daily import load_cleaned_universe

PROBABILITY_COLUMNS = ["p_down", "p_flat", "p_up"]
DIRECTIONS = np.array(["down", "flat", "up"])


@cache
def out_of_fold() -> pd.DataFrame:
    frame = pd.read_csv(OOF_PATH, usecols=["time", "symbol", "model", *PROBABILITY_COLUMNS], parse_dates=["time"])
    return frame[frame["model"] == MODEL_NAME].drop(columns="model")


def live_log() -> pd.DataFrame:
    return pd.read_csv(LOG_PATH, parse_dates=["time"])


def with_direction(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.assign(direction=DIRECTIONS[frame[PROBABILITY_COLUMNS].to_numpy().argmax(axis=1)])


def realized_direction(close: pd.Series) -> pd.Series:
    """Direction of the next session, classified with the label threshold; unknown for the last session."""
    change = np.log(close.shift(-1) / close)
    realized = pd.Series(np.where(change > THRESHOLD, "up", np.where(change < -THRESHOLD, "down", "flat")), index=close.index)
    return realized.where(change.notna())


def daily_prediction(date: pd.Timestamp, row: pd.Series) -> DailyPrediction:
    correct = None if pd.isna(row["realized"]) else bool(row["realized"] == row["direction"])
    return DailyPrediction(date=f"{date:%Y-%m-%d}", source=row["source"], correct=correct, p_down=row["p_down"],
                           p_flat=row["p_flat"], p_up=row["p_up"], direction=row["direction"])


def latest_predictions() -> LatestPredictions:
    log = live_log()
    date = log["time"].max()
    frame = with_direction(log[log["time"] == date].sort_values("rank"))
    return LatestPredictions(
        date=f"{date:%Y-%m-%d}", trained_until=f"{trained_until():%Y-%m-%d}", in_sample=bool(date <= trained_until()),
        rows=[PredictionRow(symbol=r.symbol, rank=int(r.rank), score=r.score, p_down=r.p_down, p_flat=r.p_flat, p_up=r.p_up,
                            direction=r.direction) for r in frame.itertuples()],
    )


def symbol_predictions(symbol: str, days: int) -> SymbolPredictions:
    candles = load_cleaned_universe([symbol], LIVE_DIR)[symbol].tail(days).reset_index(drop=True)
    cutoff = trained_until()
    oos, live = out_of_fold(), live_log()
    history = pd.concat([
        oos[oos["symbol"] == symbol].assign(source="oos"),
        live[(live["symbol"] == symbol) & (live["time"] > cutoff)].assign(source="live"),
    ])
    history = with_direction(history.drop_duplicates("time", keep="last").set_index("time"))
    merged = candles.set_index("time").join(history[[*PROBABILITY_COLUMNS, "direction", "source"]], how="left")
    merged["realized"] = realized_direction(merged["close"])
    predicted = merged.dropna(subset=["direction"])

    predictions = [daily_prediction(date, row) for date, row in predicted.iterrows()]
    judged = [p for p in predictions if p.correct is not None]
    last_date = f"{candles['time'].iloc[-1]:%Y-%m-%d}"
    return SymbolPredictions(
        symbol=symbol, trained_until=f"{cutoff:%Y-%m-%d}", last_oos_date=f"{oos['time'].max():%Y-%m-%d}",
        candles=[Candle(date=f"{r.time:%Y-%m-%d}", open=r.open, high=r.high, low=r.low, close=r.close) for r in candles.itertuples()],
        predictions=predictions,
        next_session=next((p for p in predictions if p.date == last_date), None),
        hit_rate=HitRate(correct=sum(p.correct for p in judged), total=len(judged)) if judged else None,
    )


def known_symbols() -> list[str]:
    return model_metadata()["symbols"]
