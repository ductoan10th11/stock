from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Direction = Literal["up", "flat", "down"]


class Probabilities(BaseModel):
    p_down: float
    p_flat: float
    p_up: float
    direction: Direction


class PredictionRow(Probabilities):
    symbol: str
    rank: int
    score: float


class LatestPredictions(BaseModel):
    date: str
    trained_until: str
    in_sample: bool
    rows: list[PredictionRow]


class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float


class DailyPrediction(Probabilities):
    date: str
    source: Literal["oos", "live"]
    correct: bool | None


class HitRate(BaseModel):
    correct: int
    total: int


class SymbolStat(BaseModel):
    symbol: str
    correct: int
    total: int


class ReviewList(BaseModel):
    """Out-of-fold accuracy of every symbol over the resolved window; first/last bound what can be asked for."""

    start: str
    end: str
    first_date: str
    last_date: str
    correct: int
    total: int
    rows: list[SymbolStat]


class SymbolPredictions(BaseModel):
    symbol: str
    trained_until: str
    last_oos_date: str
    candles: list[Candle]
    predictions: list[DailyPrediction]
    next_session: DailyPrediction | None
    hit_rate: HitRate | None
