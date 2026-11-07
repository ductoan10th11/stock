"""Out-of-fold predictions against the real candles of a chosen window, to judge the model without any trading rule."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from app.schemas.predictions import Candle, HitRate, ReviewList, SymbolPredictions, SymbolStat
from app.services.market import Market
from app.services.predictions import (
    PROBABILITY_COLUMNS, daily_prediction, out_of_fold, realized_direction, with_direction,
)

SPAN_DAYS = {"week": 7, "month": 30, "year": 365}
# shortcut: a longer window is clamped to its last 800 days so the chart stays readable, upgrade by aggregating candles.
MAX_CHART_DAYS = 800


class ModelReview:
    def __init__(self, market: Market):
        self.market = market
        self._merged = lru_cache(maxsize=32)(self._build)

    def _build(self, symbol: str) -> pd.DataFrame:
        history = out_of_fold()
        history = with_direction(history[history["symbol"] == symbol].drop_duplicates("time").set_index("time"))
        merged = self.market.candles[symbol].set_index("time").join(history[[*PROBABILITY_COLUMNS, "direction"]], how="left")
        return merged.assign(realized=realized_direction(merged["close"]), source="oos")

    def window(self, span: str | None, start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
        """(start, end, first, last): the requested window clamped to the dates that have out-of-fold predictions."""
        times = out_of_fold()["time"]
        first, last = times.min(), times.max()
        stop = min(pd.Timestamp(end), last) if end else last
        begin = pd.Timestamp(start) if start else stop - pd.Timedelta(days=SPAN_DAYS[span or "month"])
        begin = max(begin, first)
        if begin > stop:
            raise ValueError("empty window")
        return begin, stop, first, last

    def listing(self, span: str | None, start: str | None, end: str | None) -> ReviewList:
        begin, stop, first, last = self.window(span, start, end)
        rows = []
        for symbol in self.market.candles:
            judged = self._merged(symbol).loc[begin:stop].dropna(subset=["direction", "realized"])
            rows.append(SymbolStat(symbol=symbol, correct=int((judged["direction"] == judged["realized"]).sum()), total=len(judged)))
        rows.sort(key=lambda row: (-(row.correct / row.total if row.total else 0), row.symbol))
        return ReviewList(start=f"{begin:%Y-%m-%d}", end=f"{stop:%Y-%m-%d}", first_date=f"{first:%Y-%m-%d}", last_date=f"{last:%Y-%m-%d}",
                          correct=sum(r.correct for r in rows), total=sum(r.total for r in rows), rows=rows)

    def detail(self, symbol: str, span: str | None, start: str | None, end: str | None) -> SymbolPredictions:
        begin, stop, _, _ = self.window(span, start, end)
        view = self._merged(symbol).loc[max(begin, stop - pd.Timedelta(days=MAX_CHART_DAYS)):stop]
        predictions = [daily_prediction(date, row) for date, row in view.dropna(subset=["direction"]).iterrows()]
        judged = [p for p in predictions if p.correct is not None]
        end_date = f"{stop:%Y-%m-%d}"
        return SymbolPredictions(
            symbol=symbol, trained_until=end_date, last_oos_date=end_date,
            candles=[Candle(date=f"{date:%Y-%m-%d}", open=row.open, high=row.high, low=row.low, close=row.close) for date, row in view.iterrows()],
            predictions=predictions, next_session=None,
            hit_rate=HitRate(correct=sum(p.correct for p in judged), total=len(judged)) if judged else None,
        )
