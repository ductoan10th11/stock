"""Backtest runs on the out-of-fold model scores and the classic alpha signals, with per-request caching."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import numpy as np
import pandas as pd

from app.schemas.backtest import BacktestRequest, BacktestResponse, Curve, MetricsRow, Table, TableRow
from app.services.catalog import (
    BLEND, EQUAL_WEIGHT_COLOR, EQUAL_WEIGHT_LABEL, MODEL, RANDOM_LABEL, STRATEGY_BY_ID, STRATEGY_IDS, VNINDEX_COLOR,
    VNINDEX_LABEL,
)
from app.services.engine import (
    FEE_SCALES, Constraints, Params, benchmark_returns, evaluate, net, net_alpha, random_selection, simulate,
)
from app.services.market import Market, blend, execution_returns, fill_constraints
from panel_experiments import CONFIRM_START

TRIALS = len(STRATEGY_IDS)


def slice_period(frame: pd.DataFrame | pd.Series, period: str):
    if period == "dev":
        return frame[frame.index < CONFIRM_START]
    if period == "confirm":
        return frame[frame.index >= CONFIRM_START]
    return frame


def wealth(daily: pd.Series) -> pd.Series:
    return (1.0 + daily.fillna(0.0)).cumprod()


def verdict(adjusted_low: float) -> str:
    if pd.isna(adjusted_low):
        return "unknown"
    return "significant" if adjusted_low > 0 else "insufficient"


def yearly_returns(daily: pd.Series) -> pd.Series:
    return (1.0 + daily.fillna(0.0)).groupby(daily.index.year).prod() - 1.0


def plain(params: Params) -> Params:
    """The profit rule and score sizing read the model's score (probability up minus down); other signals are raw values."""
    return replace(params, min_score=-np.inf, sizing="equal", sell_score=None)


def metrics_row(key: str, label: str, kind: str, values: dict) -> MetricsRow:
    row = MetricsRow(key=key, label=label, kind=kind, **{k: v for k, v in values.items() if k in MetricsRow.model_fields})
    if kind == "strategy":
        row.verdict = verdict(values["alpha_adj_low"])
    return row


class BacktestService:
    def __init__(self, market: Market):
        self.market = market
        self._book = lru_cache(maxsize=256)(self._run_book)
        self._random = lru_cache(maxsize=256)(self._run_random)
        self._response = lru_cache(maxsize=64)(lambda key: self._compute(BacktestRequest.model_validate_json(key)))

    @property
    def ready(self) -> bool:
        return MODEL in self.market.signals

    def _constraints(self, execution: str, capital: float, limits: bool) -> Constraints | None:
        return Constraints(*fill_constraints(self.market.prices, execution, capital)) if limits else None

    def _window_returns(self, execution: str) -> tuple[pd.Index, pd.DataFrame]:
        window = self.market.signals[MODEL].dropna(how="all").index
        returns = execution_returns(self.market.prices.open, self.market.prices.close, execution)
        return window[returns.reindex(window).notna().any(axis=1).to_numpy()], returns

    def _run_book(self, weights: tuple, params: Params, execution: str, capital: float, limits: bool) -> pd.DataFrame:
        window, returns = self._window_returns(execution)
        score = blend(self.market.signals, dict(weights)).loc[window]
        return simulate(score, returns, params, self._constraints(execution, capital, limits))

    def _run_random(self, params: Params, execution: str, fee_scale: float, slippage: float, capital: float,
                    limits: bool, period: str) -> dict:
        window, returns = self._window_returns(execution)
        availability = slice_period(self.market.signals[MODEL].loc[window], period)
        return random_selection(returns, availability, params, fee_scale, slippage,
                                self._constraints(execution, capital, limits))

    def run(self, request: BacktestRequest) -> BacktestResponse:
        return self._response(request.model_dump_json())

    def random_baseline(self, request: BacktestRequest) -> MetricsRow:
        """Split from `run` because its 30 simulated portfolios cost more than everything else together."""
        values = self._random(plain(request.params.to_engine()), request.execution, request.fee_scale,
                              request.slippage_bps, request.capital, request.limits, request.period)
        return metrics_row("random", RANDOM_LABEL, "random", values)

    def _compute(self, request: BacktestRequest) -> BacktestResponse:
        market, params = self.market, request.params.to_engine()
        books = {}
        for name in request.strategies:
            weights = request.blend_weights if name == BLEND else {name: 1.0}
            strategy_params = params if name == MODEL else plain(params)
            book = self._book(tuple(sorted(weights.items())), strategy_params, request.execution, request.capital, request.limits)
            books[name] = slice_period(book, request.period)

        first_book = next(iter(books.values()))
        index = first_book.index
        returns = execution_returns(market.prices.open, market.prices.close, request.execution)
        benchmark = benchmark_returns(returns, index)
        index_daily = execution_returns(market.index["open"], market.index["close"], request.execution)
        vnindex = index_daily.reindex(index).fillna(0.0)
        daily = {name: pd.Series(net(book, request.fee_scale, request.slippage_bps), index=index) for name, book in books.items()}

        def as_book(gross: pd.Series, holdings: int) -> pd.DataFrame:
            return first_book.assign(gross=gross, buy_turnover=0.0, sell_turnover=0.0, holdings=holdings)

        metrics = [
            metrics_row(name, STRATEGY_BY_ID[name].label, "strategy",
                        evaluate(book, benchmark, request.fee_scale, request.slippage_bps, TRIALS))
            for name, book in books.items()
        ]
        metrics += [
            metrics_row("equal_weight", EQUAL_WEIGHT_LABEL, "benchmark", evaluate(as_book(benchmark, 19), benchmark, 0.0)),
            metrics_row("vnindex", VNINDEX_LABEL, "benchmark", evaluate(as_book(vnindex, 1), benchmark, 0.0)),
        ]

        curve_inputs = [(name, STRATEGY_BY_ID[name].label, STRATEGY_BY_ID[name].color, "solid", wealth(series))
                        for name, series in daily.items()]
        curve_inputs += [("equal_weight", EQUAL_WEIGHT_LABEL, EQUAL_WEIGHT_COLOR, "dash", wealth(benchmark)),
                         ("vnindex", VNINDEX_LABEL, VNINDEX_COLOR, "dot", wealth(vnindex))]
        curves = [Curve(key=key, label=label, color=color, dash=dash, wealth=curve.tolist(),
                        drawdown=(curve / curve.cummax() - 1.0).tolist())
                  for key, label, color, dash, curve in curve_inputs]

        yearly = pd.DataFrame({STRATEGY_BY_ID[name].label: yearly_returns(series) for name, series in daily.items()})
        yearly[EQUAL_WEIGHT_LABEL] = yearly_returns(benchmark)
        sensitivity = pd.DataFrame({
            STRATEGY_BY_ID[name].label: {f"×{scale:g}": net_alpha(book, benchmark, scale, request.slippage_bps)
                                         for scale in FEE_SCALES}
            for name, book in books.items()
        })

        return BacktestResponse(
            start=f"{index[0]:%Y-%m-%d}", end=f"{index[-1]:%Y-%m-%d}", sessions=len(index),
            dates=[f"{date:%Y-%m-%d}" for date in index], metrics=metrics, curves=curves,
            yearly=to_table(yearly), fee_sensitivity=to_table(sensitivity),
        )


def to_table(frame: pd.DataFrame) -> Table:
    """Rows are the frame's columns (strategies); columns are its index (years or fee scales)."""
    return Table(columns=[str(label) for label in frame.index],
                 rows=[TableRow(label=str(name), values=frame[name].replace({np.nan: None}).tolist()) for name in frame.columns])
